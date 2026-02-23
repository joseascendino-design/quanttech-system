import requests
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
from datetime import datetime
import warnings
import threading
import traceback
from flask import Flask, jsonify, request, Response

warnings.filterwarnings('ignore')

# ── Colorama stub (não usado no servidor, mas evita erros se importado) ──
class _ForeStub:
    def __getattr__(self, _): return ''
class _StyleStub:
    def __getattr__(self, _): return ''
Fore  = _ForeStub()
Style = _StyleStub()

def log_diagnostico(ticker, etapa, detalhes, tipo="INFO"):
    if tipo in ["ERRO", "AVISO"]:
        print(f"[{tipo}] {ticker} | {etapa}: {detalhes}")

# ══════════════════════════════════════════════════════════════
#  LÓGICA DE NEGÓCIO (mesma do quanttech.py local)
# ══════════════════════════════════════════════════════════════

def calcular_preco_justo_graham(lpa, crescimento_receita, vpa, score_total=0):
    if not lpa or not crescimento_receita or not vpa:
        return None, 0
    try:
        g = min(abs(crescimento_receita), 50)
        if lpa <= 0: return None, 0
        valor_raiz = lpa * (8.5 + 2 * g) * 4.4
        if valor_raiz <= 0: return None, 0
        valor_intrinseco = valor_raiz ** 0.5
        if not isinstance(valor_intrinseco, (int, float)) or valor_intrinseco != valor_intrinseco:
            return None, 0
        if score_total >= 70:
            multiplicador = 1 + (score_total / 100) * 0.5
            return valor_intrinseco * multiplicador, int((multiplicador - 1) * 100)
        return valor_intrinseco, 0
    except:
        return None, 0

def calcular_preco_teto(lpa, vpa, score_qualidade=0):
    if not lpa or not vpa: return None, 0
    try:
        if lpa <= 0 or vpa <= 0: return None, 0
        valor_raiz = 22.5 * lpa * vpa
        if valor_raiz <= 0: return None, 0
        valor_teto = valor_raiz ** 0.5
        if not isinstance(valor_teto, (int, float)) or valor_teto != valor_teto:
            return None, 0
        if score_qualidade >= 30:
            multiplicador = 1 + (score_qualidade / 40) * 0.3
            return valor_teto * multiplicador, int((multiplicador - 1) * 100)
        return valor_teto, 0
    except:
        return None, 0

def limpar_valor(valor_texto):
    if not valor_texto or valor_texto.strip() in ['-', '', 'N/A', '--']:
        return None
    try:
        valor_limpo = valor_texto.replace('.', '').replace(',', '.').replace('%', '').strip()
        return float(valor_limpo)
    except:
        return None

BRAPI_TOKEN = 'sDvXn4oPrWRmmZzgTo4wgC'

def buscar_dados_fundamentus(ticker):
    ticker_limpo = ticker.replace('.SA', '').upper()
    try:
        url = f"https://brapi.dev/api/quote/{ticker_limpo}?modules=summaryProfile,defaultKeyStatistics,financialData&token={BRAPI_TOKEN}"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        j = r.json()

        if not j.get('results'):
            return None

        res = j['results'][0]

        def g(d, *keys):
            for k in keys:
                if isinstance(d, dict): d = d.get(k)
                else: return None
            return d

        def pct(v):
            if v is None: return None
            return round(v * 100, 2) if abs(v) < 5 else round(v, 2)

        # Dados diretos do resultado
        cotacao       = res.get('regularMarketPrice')
        nome          = res.get('longName') or res.get('shortName') or ticker_limpo
        valor_mercado = res.get('marketCap')

        # summaryProfile
        sp = res.get('summaryProfile') or {}
        setor    = sp.get('sector')
        subsetor = sp.get('industry')

        # defaultKeyStatistics
        ks = res.get('defaultKeyStatistics') or {}
        pl             = ks.get('trailingPE') or res.get('priceEarnings')
        pvp            = ks.get('priceToBook')
        lpa            = ks.get('trailingEps') or ks.get('forwardEps')
        vpa            = ks.get('bookValue')
        ev             = ks.get('enterpriseValue')
        ev_ebitda      = ks.get('enterpriseToEbitda')
        ev_ebit        = ks.get('enterpriseToRevenue')
        psr            = res.get('priceToSalesTrailing12Months') or ks.get('priceToSalesTrailing12Months')

        # financialData
        fd = res.get('financialData') or {}
        roe            = pct(fd.get('returnOnEquity'))
        roic           = pct(fd.get('returnOnAssets'))
        margem_bruta   = pct(fd.get('grossMargins'))
        margem_ebit    = pct(fd.get('operatingMargins'))
        margem_liquida = pct(fd.get('profitMargins'))
        ebitda         = fd.get('ebitda')
        lucro_liquido  = fd.get('netIncomeToCommon') or fd.get('freeCashflow')
        divida_total   = fd.get('totalDebt')
        caixa          = fd.get('totalCash')
        receita        = fd.get('totalRevenue')
        divida_liquida = (divida_total - caixa) if divida_total and caixa else None
        dy             = pct(res.get('dividendYield') or fd.get('dividendYield'))
        liq_corrente   = fd.get('currentRatio')
        divida_liq_ebitda = (divida_liquida / ebitda) if divida_liquida and ebitda and ebitda > 0 else None

        # Dívida bruta / patrimônio
        divida_bruta_patrim = fd.get('debtToEquity')
        if divida_bruta_patrim:
            divida_bruta_patrim = divida_bruta_patrim / 100  # Brapi retorna em %, converter

        # Giro ativos
        giro_ativos = None
        total_assets = fd.get('totalAssets') or ks.get('totalAssets')
        if receita and total_assets and total_assets > 0:
            giro_ativos = receita / total_assets

        # EBIT/Ativo
        ebit_ativo = None
        if ebitda and total_assets and total_assets > 0:
            ebit_ativo = pct(ebitda / total_assets)

        # P/EBIT
        p_ebit = None
        if cotacao and ebitda and valor_mercado and ebitda > 0:
            ebit_por_acao = ebitda / (valor_mercado / cotacao) if valor_mercado and cotacao else None
            if ebit_por_acao and ebit_por_acao > 0:
                p_ebit = cotacao / ebit_por_acao

        # Crescimento receita
        crescimento_receita = pct(fd.get('revenueGrowth') or fd.get('earningsGrowth'))

        # Valor firma
        valor_firma = ev

        # Oscilações
        oscilacoes = {}
        try:
            url_osc = f"https://brapi.dev/api/quote/{ticker_limpo}?range=1y&interval=1d&token={BRAPI_TOKEN}"
            ro = requests.get(url_osc, timeout=15)
            hist_data = ro.json().get('results', [{}])[0].get('historicalDataPrice', [])
            if hist_data and len(hist_data) > 1:
                p_hoje = hist_data[-1].get('close', 0)
                p_ontem = hist_data[-2].get('close', 0)
                p_30d   = hist_data[-22].get('close', 0) if len(hist_data) > 22 else 0
                p_12m   = hist_data[0].get('close', 0)
                if p_ontem and p_hoje: oscilacoes['dia']      = round(((p_hoje/p_ontem)-1)*100, 1)
                if p_30d   and p_hoje: oscilacoes['30_dias']  = round(((p_hoje/p_30d)-1)*100, 1)
                if p_12m   and p_hoje: oscilacoes['12_meses'] = round(((p_hoje/p_12m)-1)*100, 1)
        except: pass

        dados = {
            'ticker': ticker_limpo, 'nome': nome, 'setor': setor, 'subsetor': subsetor,
            'cotacao': cotacao, 'pl': pl, 'pvp': pvp, 'psr': psr, 'p_ebit': p_ebit,
            'ev_ebitda': ev_ebitda, 'ev_ebit': ev_ebit, 'lpa': lpa, 'vpa': vpa,
            'roe': roe, 'roic': roic, 'ebit_ativo': ebit_ativo,
            'margem_bruta': margem_bruta, 'margem_ebit': margem_ebit, 'margem_liquida': margem_liquida,
            'divida_bruta_patrim': divida_bruta_patrim, 'divida_liquida_pl': None,
            'divida_liquida_ebitda': divida_liq_ebitda, 'liquidez_corrente': liq_corrente,
            'giro_ativos': giro_ativos, 'crescimento_receita': crescimento_receita, 'div_yield': dy,
            'valor_mercado': valor_mercado, 'valor_firma': valor_firma, 'lucro_liquido': lucro_liquido,
            'oscilacoes': oscilacoes
        }
        return dados if cotacao else None

    except Exception as e:
        print(f"[ERRO] buscar_dados_fundamentus: {e}")
        traceback.print_exc()
        return None

        if not j.get('results'):
            return None

        res = j['results'][0]

        def g(d, *keys):
            """Pega valor aninhado com segurança"""
            for k in keys:
                if isinstance(d, dict):
                    d = d.get(k)
                else:
                    return None
            return d

        def pct(v):
            """Converte decimal para percentual se necessário"""
            if v is None: return None
            return v * 100 if abs(v) < 5 else v

        cotacao        = g(res, 'regularMarketPrice')
        pl             = g(res, 'priceToEarningsRatio') or g(res, 'trailingPE')
        pvp            = g(res, 'priceToBookRatio') or g(res, 'priceToBook')
        lpa            = g(res, 'eps') or g(res, 'epsTrailingTwelveMonths')
        dy             = pct(g(res, 'dividendYield'))
        valor_mercado  = g(res, 'marketCap')
        nome           = g(res, 'longName') or g(res, 'shortName') or ticker_limpo
        setor          = g(res, 'sector')
        subsetor       = g(res, 'industry')

        # Indicadores financeiros
        fd = res.get('financialData') or {}
        roe            = pct(g(fd, 'returnOnEquity'))
        roic           = pct(g(fd, 'returnOnAssets'))  # aproximação
        margem_bruta   = pct(g(fd, 'grossMargins'))
        margem_ebit    = pct(g(fd, 'operatingMargins') or g(fd, 'ebitdaMargins'))
        margem_liquida = pct(g(fd, 'profitMargins'))
        receita        = g(fd, 'totalRevenue')
        ebitda         = g(fd, 'ebitda')
        lucro_liquido  = g(fd, 'netIncomeToCommon') or g(fd, 'freeCashflow')
        divida_total   = g(fd, 'totalDebt')
        caixa          = g(fd, 'totalCash')
        divida_liquida = (divida_total - caixa) if divida_total and caixa else None

        ks = res.get('defaultKeyStatistics') or {}
        vpa            = g(ks, 'bookValue')
        ev             = g(ks, 'enterpriseValue')
        psr            = g(ks, 'priceToSalesTrailing12Months')
        ev_ebitda      = (ev / ebitda) if ev and ebitda and ebitda > 0 else None
        divida_liq_ebitda = (divida_liquida / ebitda) if divida_liquida and ebitda and ebitda > 0 else None
        divida_bruta_patrim = None
        if divida_total and vpa and valor_mercado:
            patrim = vpa * (valor_mercado / cotacao) if cotacao else None
            if patrim and patrim > 0:
                divida_bruta_patrim = divida_total / patrim

        # Crescimento receita (via histórico se disponível)
        crescimento_receita = None
        try:
            inc = res.get('incomeStatementHistory', {}).get('incomeStatementHistory', [])
            if len(inc) >= 2:
                r_new = inc[0].get('totalRevenue', {}).get('raw', 0)
                r_old = inc[-1].get('totalRevenue', {}).get('raw', 0)
                if r_old and r_old > 0 and r_new:
                    anos = len(inc) - 1
                    crescimento_receita = ((r_new / r_old) ** (1/anos) - 1) * 100
        except: pass

        # Oscilações via Brapi
        oscilacoes = {}
        try:
            url_osc = f"https://brapi.dev/api/quote/{ticker_limpo}?range=1y&interval=1d&token={BRAPI_TOKEN}"
            ro = requests.get(url_osc, timeout=15)
            hist_data = ro.json().get('results', [{}])[0].get('historicalDataPrice', [])
            if hist_data and len(hist_data) > 1:
                p_hoje = hist_data[-1].get('close', 0)
                p_ontem = hist_data[-2].get('close', 0) if len(hist_data) > 1 else 0
                p_30d   = hist_data[-22].get('close', 0) if len(hist_data) > 22 else 0
                p_12m   = hist_data[0].get('close', 0)
                if p_ontem and p_hoje: oscilacoes['dia']     = ((p_hoje/p_ontem)-1)*100
                if p_30d   and p_hoje: oscilacoes['30_dias'] = ((p_hoje/p_30d)-1)*100
                if p_12m   and p_hoje: oscilacoes['12_meses']= ((p_hoje/p_12m)-1)*100
        except: pass

        # Valor firma
        valor_firma = ev

        dados = {
            'ticker': ticker_limpo, 'nome': nome, 'setor': setor, 'subsetor': subsetor,
            'cotacao': cotacao, 'pl': pl, 'pvp': pvp, 'psr': psr, 'p_ebit': None,
            'ev_ebitda': ev_ebitda, 'ev_ebit': None, 'lpa': lpa, 'vpa': vpa,
            'roe': roe, 'roic': roic, 'ebit_ativo': None,
            'margem_bruta': margem_bruta, 'margem_ebit': margem_ebit, 'margem_liquida': margem_liquida,
            'divida_bruta_patrim': divida_bruta_patrim, 'divida_liquida_pl': None,
            'divida_liquida_ebitda': divida_liq_ebitda, 'liquidez_corrente': None,
            'giro_ativos': None, 'crescimento_receita': crescimento_receita, 'div_yield': dy,
            'valor_mercado': valor_mercado, 'valor_firma': valor_firma, 'lucro_liquido': lucro_liquido,
            'oscilacoes': oscilacoes
        }
        return dados if cotacao else None

    except Exception as e:
        print(f"[ERRO] buscar_dados_fundamentus: {e}")
        traceback.print_exc()
        return None
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table')
        if not tables:
            return None

        dados = {
            'ticker': ticker_limpo, 'nome': None, 'setor': None, 'subsetor': None,
            'cotacao': None, 'pl': None, 'pvp': None, 'psr': None, 'p_ebit': None,
            'ev_ebitda': None, 'ev_ebit': None, 'lpa': None, 'vpa': None,
            'roe': None, 'roic': None, 'ebit_ativo': None,
            'margem_bruta': None, 'margem_ebit': None, 'margem_liquida': None,
            'divida_bruta_patrim': None, 'divida_liquida_pl': None,
            'divida_liquida_ebitda': None, 'liquidez_corrente': None,
            'giro_ativos': None, 'crescimento_receita': None, 'div_yield': None,
            'valor_mercado': None, 'valor_firma': None, 'lucro_liquido': None,
            'oscilacoes': {}
        }

        # Extrair todos os pares label→valor das tabelas
        pares = {}
        all_cells = []
        for table in tables:
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                textos = [c.get_text(strip=True) for c in cells]
                all_cells.extend(textos)
                # Pares consecutivos label→valor
                for i in range(0, len(textos) - 1, 2):
                    if textos[i]:
                        pares[textos[i]] = textos[i+1] if i+1 < len(textos) else ''
                # Também mapear posição impar
                for i in range(len(textos)-1):
                    if textos[i]:
                        pares[textos[i]] = textos[i+1]

        def buscar(labels):
            """Busca valor por múltiplos labels possíveis, insensível a acento/case"""
            import unicodedata
            def norm(s):
                return unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower().strip()
            for label in labels:
                nl = norm(label)
                for k, v in pares.items():
                    if norm(k) == nl and v and v.strip() not in ['-','','N/A','--']:
                        return limpar_valor(v)
                # Busca parcial
                for k, v in pares.items():
                    if nl in norm(k) and v and v.strip() not in ['-','','N/A','--']:
                        return limpar_valor(v)
            return None

        def buscar_raw(labels):
            """Retorna texto bruto sem limpar"""
            import unicodedata
            def norm(s):
                return unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower().strip()
            for label in labels:
                nl = norm(label)
                for k, v in pares.items():
                    if norm(k) == nl and v and v.strip() not in ['-','','N/A','--']:
                        return v.strip()
            return None

        # Nome da empresa
        try:
            for table in tables:
                cells = table.find_all('td')
                for i, c in enumerate(cells):
                    if ticker_limpo.upper() in c.get_text(strip=True).upper() and i+1 < len(cells):
                        nome_candidato = cells[i+1].get_text(strip=True)
                        if len(nome_candidato) > 3:
                            dados['nome'] = nome_candidato
                            break
                if dados['nome']:
                    break
            if not dados['nome'] and len(all_cells) > 2:
                dados['nome'] = all_cells[1] if len(all_cells[1]) > 3 else all_cells[2]
        except: pass

        # Setor/Subsetor
        for i, c in enumerate(all_cells):
            if c in ['Setor', 'Setor:'] and i+1 < len(all_cells):
                dados['setor'] = all_cells[i+1]
            if c in ['Subsetor', 'Subsetor:'] and i+1 < len(all_cells):
                dados['subsetor'] = all_cells[i+1]

        # Mapeamento robusto com múltiplos labels por campo
        mapa = {
            'cotacao':               ['Cotacao', 'Cot.', 'Cotação'],
            'pl':                    ['P/L', 'P/L '],
            'pvp':                   ['P/VP', 'P/VP '],
            'psr':                   ['PSR'],
            'p_ebit':                ['P/EBIT'],
            'ev_ebitda':             ['EV/EBITDA'],
            'ev_ebit':               ['EV/EBIT'],
            'lpa':                   ['LPA'],
            'vpa':                   ['VPA'],
            'roe':                   ['ROE'],
            'roic':                  ['ROIC'],
            'ebit_ativo':            ['EBIT / Ativo', 'EBIT/Ativo', 'EBIT / Ativo '],
            'margem_bruta':          ['Marg. Bruta', 'Margem Bruta', 'Marg Bruta'],
            'margem_ebit':           ['Marg. EBIT', 'Margem EBIT', 'Marg EBIT'],
            'margem_liquida':        ['Marg. Liquida', 'Margem Liquida', 'Marg. Líquida', 'Margem Líquida'],
            'divida_bruta_patrim':   ['Div. Bruta/ Patrim.', 'Div. Bruta/Patrim.', 'Div Bruta/ Patrim', 'Divida Bruta/ Patrim'],
            'divida_liquida_ebitda': ['Div. Liq./EBITDA', 'Div. Líq./EBITDA', 'Divida Liq./EBITDA'],
            'divida_liquida_pl':     ['Div. Liq./Patrim.', 'Div. Líq./Patrim.', 'Divida Liq./Patrim'],
            'liquidez_corrente':     ['Liquidez Corr.', 'Liquidez Corrente', 'Liq. Corrente'],
            'giro_ativos':           ['Giro Ativos', 'Giro dos Ativos'],
            'crescimento_receita':   ['Cresc. Rec.5a', 'Cresc. Rec. 5a', 'Cresc Rec 5a', 'Crescimento Rec 5a', 'Cresc. Rec.5anos'],
            'div_yield':             ['Div. Yield', 'Dividend Yield', 'DY'],
        }

        for campo, labels in mapa.items():
            val = buscar(labels)
            if val is not None:
                dados[campo] = val

        # Valores absolutos (busca por texto parcial)
        for i, c in enumerate(all_cells):
            cl = c.lower()
            if 'valor de mercado' in cl and i+1 < len(all_cells):
                try: dados['valor_mercado'] = float(all_cells[i+1].replace('.','').replace(',','.').strip())
                except: pass
            if 'valor da firma' in cl and i+1 < len(all_cells):
                try: dados['valor_firma'] = float(all_cells[i+1].replace('.','').replace(',','.').strip())
                except: pass
            if 'lucro l' in cl and 'quido' in cl and i+1 < len(all_cells):
                try: dados['lucro_liquido'] = float(all_cells[i+1].replace('.','').replace(',','.').strip())
                except: pass

        # Oscilações
        osc_labels = {
            'dia':      ['Dia', '1 Dia'],
            'mes':      ['Mes', 'Mês', '1 Mes', '1 Mês'],
            '30_dias':  ['30 dias', '30 Dias'],
            '12_meses': ['12 meses', '12 Meses'],
            '2026':     ['2026'], '2025': ['2025'],
            '2024':     ['2024'], '2023': ['2023'], '2022': ['2022'],
        }
        for chave, labels in osc_labels.items():
            val = buscar(labels)
            if val is not None:
                dados['oscilacoes'][chave] = val

        return dados if dados['cotacao'] else None

    except Exception as e:
        print(f"[ERRO] buscar_dados_fundamentus: {e}")
        traceback.print_exc()
        return None

def calcular_score_consolidado(dados):
    score = {'qualidade': 0, 'valuation': 0, 'crescimento': 0, 'solidez': 0,
             'total': 0, 'eh_banco': False, 'empresa_crescimento': False}

    # Detectar banco
    nome = (dados.get('nome') or '').lower()
    setor = (dados.get('setor') or '').lower()
    eh_banco = any(x in nome+setor for x in ['banco','financ','bradesco','itaú','itau','santander','btg','xp invest','caixa'])
    score['eh_banco'] = eh_banco

    # QUALIDADE (40pts)
    roe = dados.get('roe')
    if roe:
        if roe >= 20: score['qualidade'] += 15
        elif roe >= 15: score['qualidade'] += 10
        elif roe >= 10: score['qualidade'] += 5

    roic = dados.get('roic')
    if roic:
        if roic >= 15: score['qualidade'] += 10
        elif roic >= 10: score['qualidade'] += 7
        elif roic >= 6: score['qualidade'] += 3

    ml = dados.get('margem_liquida')
    if ml:
        if ml >= 15: score['qualidade'] += 10
        elif ml >= 8: score['qualidade'] += 6
        elif ml >= 3: score['qualidade'] += 2

    me = dados.get('margem_ebit')
    if me:
        if me >= 20: score['qualidade'] += 5
        elif me >= 10: score['qualidade'] += 3

    # VALUATION (30pts)
    pl = dados.get('pl')
    pvp = dados.get('pvp')
    dy = dados.get('div_yield')
    cr = dados.get('crescimento_receita') or 0
    empresa_crescimento = roic and roic >= 15 and cr >= 15
    score['empresa_crescimento'] = empresa_crescimento

    if pl and pl > 0:
        if empresa_crescimento:
            peg = pl / max(cr, 1)
            if peg < 1: score['valuation'] += 15
            elif peg < 1.5: score['valuation'] += 10
            elif peg < 2: score['valuation'] += 5
        else:
            if pl < 8: score['valuation'] += 15
            elif pl < 15: score['valuation'] += 10
            elif pl < 25: score['valuation'] += 5

    if pvp:
        if pvp < 1: score['valuation'] += 10
        elif pvp < 2: score['valuation'] += 6
        elif pvp < 3: score['valuation'] += 2

    if dy:
        if dy >= 8: score['valuation'] += 5
        elif dy >= 5: score['valuation'] += 3
        elif dy >= 3: score['valuation'] += 1

    # CRESCIMENTO (20pts)
    if cr:
        if cr >= 20: score['crescimento'] += 15
        elif cr >= 10: score['crescimento'] += 10
        elif cr >= 5: score['crescimento'] += 5
    mb = dados.get('margem_bruta')
    if mb and mb >= 30: score['crescimento'] += 5

    # SOLIDEZ (10pts)
    if eh_banco:
        if roe and roe >= 15: score['solidez'] += 5
        if ml and ml >= 20: score['solidez'] += 5
    else:
        db = dados.get('divida_bruta_patrim')
        if db is not None:
            if db < 0.3: score['solidez'] += 5
            elif db < 1: score['solidez'] += 3
            elif db < 2: score['solidez'] += 1
        lc = dados.get('liquidez_corrente')
        if lc:
            if lc >= 2: score['solidez'] += 5
            elif lc >= 1.5: score['solidez'] += 3
            elif lc >= 1: score['solidez'] += 1

    score['qualidade']   = min(score['qualidade'], 40)
    score['valuation']   = min(score['valuation'], 30)
    score['crescimento'] = min(score['crescimento'], 20)
    score['solidez']     = min(score['solidez'], 10)
    score['total'] = score['qualidade'] + score['valuation'] + score['crescimento'] + score['solidez']
    return score

def gerar_alertas_inteligentes(dados, ticker):
    oportunidades = []
    bandeiras = []
    pl = dados.get('pl'); pvp = dados.get('pvp'); roe = dados.get('roe')
    dy = dados.get('div_yield'); cr = dados.get('crescimento_receita')
    db = dados.get('divida_bruta_patrim'); ml = dados.get('margem_liquida')
    roic = dados.get('roic')

    if pl and 0 < pl < 8:
        oportunidades.append(f"💎 P/L muito baixo ({pl:.1f}) - Possível subvalorização")
    if pvp and pvp < 1:
        oportunidades.append(f"📊 P/VP abaixo de 1 ({pvp:.2f}) - Ativo abaixo do patrimônio")
    if roe and roe >= 20:
        oportunidades.append(f"🚀 ROE excepcional ({roe:.1f}%) - Alta rentabilidade!")
    if dy and dy >= 8:
        oportunidades.append(f"💰 Dividend Yield atrativo ({dy:.1f}%) - Renda passiva")
    if cr and cr >= 15:
        oportunidades.append(f"📈 Crescimento forte ({cr:.1f}% a.a.) - Empresa em expansão")
    if roic and roic >= 20:
        oportunidades.append(f"⭐ ROIC excelente ({roic:.1f}%) - Retorno superior ao capital")

    if pl and pl > 40:
        bandeiras.append(f"⚠️ P/L muito alto ({pl:.1f}) - Risco de sobrevalorização")
    if db and db > 3:
        bandeiras.append(f"🚨 Dívida elevada ({db:.1f}x patrimônio)")
    if ml and ml < 0:
        bandeiras.append(f"❌ Margem líquida negativa ({ml:.1f}%) - Empresa dando prejuízo")
    if cr and cr < -10:
        bandeiras.append(f"📉 Queda de receita ({cr:.1f}%) - Negócio em retração")

    return {'oportunidades': oportunidades, 'bandeiras_vermelhas': bandeiras}

def simulacao_investimento(ticker_yf, valor_inicial=1000.0, ano_inicio=2019):
    try:
        acao = yf.Ticker(ticker_yf)
        data_inicio = f"{ano_inicio}-01-01"
        hist = acao.history(start=data_inicio, auto_adjust=True)
        if hist.empty or len(hist) < 10:
            return None
        dividendos = acao.history(start=data_inicio, auto_adjust=True)['Dividends']
        dividendos = dividendos[dividendos > 0]

        preco_entrada = hist['Close'].iloc[0]
        preco_atual   = hist['Close'].iloc[-1]
        data_entrada  = hist.index[0].strftime('%d/%m/%Y')

        acoes_iniciais = valor_inicial / preco_entrada
        acoes_com_reinv = acoes_iniciais
        total_reinvestido = 0.0
        historico_divs = []

        for data, div_por_acao in dividendos.items():
            if div_por_acao <= 0: continue
            try:
                preco_na_data = hist['Close'].asof(data)
                if pd.isna(preco_na_data) or preco_na_data <= 0: continue
                recebido = acoes_com_reinv * div_por_acao
                novas_acoes = recebido / preco_na_data
                acoes_com_reinv += novas_acoes
                total_reinvestido += recebido
                historico_divs.append({
                    'data': data.strftime('%m/%Y'),
                    'valor_unit': div_por_acao,
                    'recebido': recebido
                })
            except: continue

        valor_com_reinv     = acoes_com_reinv * preco_atual
        valor_sem_reinv     = acoes_iniciais  * preco_atual
        ganho_reinvestimento = valor_com_reinv - valor_sem_reinv

        anos = max((datetime.now() - hist.index[0].to_pydatetime().replace(tzinfo=None)).days / 365.25, 0.1)
        cagr_sem = ((valor_sem_reinv / valor_inicial) ** (1 / anos) - 1) * 100
        cagr_com = ((valor_com_reinv / valor_inicial) ** (1 / anos) - 1) * 100

        return {
            'preco_entrada': preco_entrada, 'preco_atual': preco_atual,
            'data_entrada': data_entrada,
            'acoes_iniciais': acoes_iniciais, 'acoes_com_reinv': acoes_com_reinv,
            'valor_sem_reinv_total': valor_sem_reinv,
            'valor_com_reinv': valor_com_reinv,
            'ganho_reinvestimento': ganho_reinvestimento,
            'total_reinvestido': total_reinvestido,
            'retorno_sem': ((valor_sem_reinv / valor_inicial) - 1) * 100,
            'retorno_com': ((valor_com_reinv  / valor_inicial) - 1) * 100,
            'cagr_sem': cagr_sem, 'cagr_com': cagr_com,
            'num_dividendos': len(historico_divs),
            'historico_dividendos': historico_divs,
            'anos': round(anos, 1)
        }
    except Exception as e:
        print(f"[ERRO] simulacao_investimento: {e}")
        return None

# ══════════════════════════════════════════════════════════════
#  GERADOR DE HTML DO RELATÓRIO
# ══════════════════════════════════════════════════════════════

def gerar_html_relatorio(ticker, dados, scores, insights, sim,
                         preco_justo=None, preco_teto=None,
                         variacao_3m=None, acima_ema50=None):

    def cor(val, bom, ok, inv=False):
        if val is None: return 'neutral'
        if inv: return 'green' if val<=bom else ('yellow' if val<=ok else 'red')
        return 'green' if val>=bom else ('yellow' if val>=ok else 'red')

    def fmt(val, d=2, s=''):
        return f'{val:.{d}f}{s}' if val is not None else '—'

    def fmt_bi(val):
        if val is None: return '—'
        if abs(val) >= 1e9: return f'R$ {val/1e9:.2f} bi'
        if abs(val) >= 1e6: return f'R$ {val/1e6:.0f} M'
        return f'R$ {val:.0f}'

    def card(label, valor, cls='neutral'):
        return f'<div class="ind-card {cls}"><div class="ind-label">{label}</div><div class="ind-value">{valor}</div></div>'

    def barra(v, mx, cor_barra):
        pct = min((v/mx)*100, 100)
        return f'<div class="score-bar-fill" style="width:{pct}%;background:{cor_barra}"></div>'

    score_total = scores['total']
    if score_total >= 80:   slabel, scolor = 'EXCELENTE', '#00ff88'
    elif score_total >= 65: slabel, scolor = 'MUITO BOM', '#4da6ff'
    elif score_total >= 50: slabel, scolor = 'BOM',       '#ffd700'
    elif score_total >= 35: slabel, scolor = 'REGULAR',   '#ff9900'
    else:                   slabel, scolor = 'FRACO',     '#ff4444'

    eh_banco = scores.get('eh_banco', False)
    ticker_clean = ticker.replace('.SA','')
    now = datetime.now().strftime('%d/%m/%Y %H:%M')

    # VALUATION
    val_html = ''
    if preco_justo and dados.get('cotacao'):
        cot = dados['cotacao']
        dj  = ((preco_justo - cot)/cot)*100
        dt  = ((preco_teto  - cot)/cot)*100 if preco_teto else None
        if cot < preco_justo*0.7:   sv, cv = 'MUITO SUBVALORIZADA', '#00ff88'
        elif cot < preco_justo*0.9: sv, cv = 'SUBVALORIZADA',       '#00cc66'
        elif cot < preco_justo*1.1: sv, cv = 'PREÇO JUSTO',         '#ffd700'
        elif cot < preco_justo*1.3: sv, cv = 'LEVEMENTE CARA',      '#ff9900'
        else:                       sv, cv = 'SOBREVALORIZADA',      '#ff4444'
        vmax    = max(cot, preco_justo, preco_teto or 0)*1.15
        pc      = (cot/vmax)*100
        pj      = (preco_justo/vmax)*100
        pt_html = f'<div class="vbar-marker teto" style="left:{(preco_teto/vmax)*100:.1f}%"></div>' if preco_teto else ''
        dt_html = ''
        if dt is not None:
            cc = '#00ff88' if dt>0 else '#ff4444'
            dt_html = f'<div class="val-item"><span>Preço Teto</span><strong>R$ {preco_teto:.2f}</strong><span style="color:{cc}">{dt:+.1f}%</span></div>'
        val_html = f'''<div class="section">
          <div class="section-title">💎 VALUATION</div>
          <div class="val-status" style="color:{cv}">{sv}</div>
          <div class="vbar-wrap"><div class="vbar-track">
            <div class="vbar-fill" style="width:{pc:.1f}%;background:{cv}"></div>
            <div class="vbar-marker justo" style="left:{pj:.1f}%"></div>
            {pt_html}<div class="vbar-cotacao" style="left:{pc:.1f}%">▼</div>
          </div></div>
          <div class="val-items">
            <div class="val-item"><span>Cotação</span><strong>R$ {cot:.2f}</strong></div>
            <div class="val-item"><span>Preço Justo</span><strong>R$ {preco_justo:.2f}</strong>
              <span style="color:{'#00ff88' if dj>0 else '#ff4444'}">{dj:+.1f}%</span></div>
            {dt_html}
          </div></div>'''

    # SIMULAÇÃO
    sim_html = ''
    if sim:
        chart_bars = ''
        if sim['historico_dividendos']:
            max_r = max(d['recebido'] for d in sim['historico_dividendos'])
            for d in sim['historico_dividendos']:
                h    = (d['recebido']/max_r)*100 if max_r>0 else 0
                tipo = 'JCP' if d['valor_unit']<0.05 else 'DIV'
                ct   = '#ffd700' if tipo=='JCP' else '#00ff88'
                chart_bars += f'<div class="div-bar-wrap"><div class="div-bar-val">R${d["recebido"]:.0f}</div><div class="div-bar-col"><div class="div-bar-fill" style="height:{h:.0f}%;background:{ct}"></div></div><div class="div-bar-date">{d["data"]}</div><div class="div-bar-tipo" style="color:{ct}">{tipo}</div></div>'
        gc = '#00ff88' if sim['ganho_reinvestimento']>0 else '#ff4444'
        cs = '#00ff88' if sim['retorno_sem']>0 else '#ff4444'
        sim_html = f'''<div class="section" id="sim-section">
          <div class="section-title">💸 SIMULAÇÃO
            <span class="sim-controls">
              R$<input type="number" id="sim-valor" value="1000" min="100" step="100">
              em <input type="number" id="sim-ano" value="2019" min="2010" max="2024" step="1">
              <button onclick="recalcularSim()">▶ RECALCULAR</button>
              <span id="sim-status"></span>
            </span>
          </div>
          <div id="sim-content">
            <div class="sim-grid">
              <div class="sim-card"><div class="sim-label">📦 Sem reinvestimento</div>
                <div class="sim-value">R$ {sim["valor_sem_reinv_total"]:,.2f}</div>
                <div class="sim-ret" style="color:{cs}">{sim["retorno_sem"]:+.1f}%</div>
                <div class="sim-sub">CAGR {sim["cagr_sem"]:.1f}% a.a.</div></div>
              <div class="sim-card highlight"><div class="sim-label">🔄 Com reinvestimento</div>
                <div class="sim-value">R$ {sim["valor_com_reinv"]:,.2f}</div>
                <div class="sim-ret" style="color:#00ff88">{sim["retorno_com"]:+.1f}%</div>
                <div class="sim-sub">CAGR {sim["cagr_com"]:.1f}% a.a.</div></div>
              <div class="sim-card"><div class="sim-label">⚡ Ganho do reinvestimento</div>
                <div class="sim-value" style="color:{gc}">R$ {sim["ganho_reinvestimento"]:,.2f}</div>
                <div class="sim-ret" style="color:{gc}">{sim["retorno_com"]-sim["retorno_sem"]:+.1f}%</div>
                <div class="sim-sub">{sim["num_dividendos"]} pagamentos · {sim["acoes_iniciais"]:.1f}→{sim["acoes_com_reinv"]:.1f} ações</div></div>
            </div>
            <div class="sim-meta">Entrada {sim["data_entrada"]} · preço ajustado R$ {sim["preco_entrada"]:.2f} → R$ {sim["preco_atual"]:.2f} hoje</div>
            <div class="div-chart" id="div-chart-bars">{chart_bars}</div>
          </div></div>'''

    # OPORTUNIDADES / ALERTAS
    oport_html = ''
    if insights['oportunidades']:
        itens = ''.join(f'<li class="oport-item">{o}</li>' for o in insights['oportunidades'])
        oport_html = f'<div class="section oport-section"><div class="section-title">🌟 OPORTUNIDADES</div><ul>{itens}</ul></div>'
    band_html = ''
    if insights['bandeiras_vermelhas']:
        itens = ''.join(f'<li class="band-item">{b}</li>' for b in insights['bandeiras_vermelhas'])
        band_html = f'<div class="section band-section"><div class="section-title">🚨 ALERTAS</div><ul>{itens}</ul></div>'

    # OSCILAÇÕES
    osc = dados.get('oscilacoes', {})
    def osc_cell(label, chave):
        v = osc.get(chave)
        if v is None: return ''
        c = '#00ff88' if v>0 else '#ff4444'
        return f'<div class="osc-item"><span class="osc-label">{label}</span><span class="osc-val" style="color:{c}">{v:+.1f}%</span></div>'
    osc_html = f'''<div class="section"><div class="section-title">📊 OSCILAÇÕES</div><div class="osc-grid">
        {osc_cell("Dia","dia")}{osc_cell("Mês","mes")}{osc_cell("30d","30_dias")}{osc_cell("12m","12_meses")}
        {osc_cell("2026","2026")}{osc_cell("2025","2025")}{osc_cell("2024","2024")}{osc_cell("2023","2023")}{osc_cell("2022","2022")}
    </div></div>'''

    # TÉCNICA
    tec_html = ''
    if variacao_3m is not None or acima_ema50 is not None:
        cv2 = '#00ff88' if (variacao_3m or 0)>0 else '#ff4444'
        et  = '✅ Acima EMA50' if acima_ema50 else '❌ Abaixo EMA50'
        ec  = '#00ff88' if acima_ema50 else '#ff4444'
        tec_html = f'''<div class="section"><div class="section-title">📈 TÉCNICA</div><div class="tec-grid">
          <div class="ind-card neutral"><div class="ind-label">Var. 3 meses</div><div class="ind-value" style="color:{cv2}">{fmt(variacao_3m,1,'%')}</div></div>
          <div class="ind-card neutral"><div class="ind-label">Tendência</div><div class="ind-value" style="color:{ec};font-size:0.8rem">{et}</div></div>
        </div></div>'''

    # CLASSIFICAÇÃO
    if score_total >= 80:   ctxt = '⭐ COMPRA FORTE — EXCELENTE OPORTUNIDADE'
    elif score_total >= 65: ctxt = '💎 COMPRA — MUITO BOA EMPRESA'
    elif score_total >= 50: ctxt = '✓ CONSIDERAR — BOA EMPRESA'
    elif score_total >= 35: ctxt = '⚠ CAUTELA — EMPRESA REGULAR'
    else:                   ctxt = '❌ EVITAR — EMPRESA FRACA'

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>⚛️ QUANTTECH — {ticker_clean}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;700;800&display=swap');
  :root{{--bg:#0a0c10;--bg2:#111318;--bg3:#1a1d24;--border:#2a2d36;
    --green:#00ff88;--red:#ff4455;--yellow:#ffd700;--cyan:#00e5ff;
    --text:#e8eaf0;--muted:#6b7280;--accent:{scolor};}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.4;}}
  .header{{background:linear-gradient(135deg,#0d1117,#111827,#0d1117);border-bottom:1px solid var(--border);
    padding:8px 16px;display:flex;align-items:center;justify-content:space-between;
    position:sticky;top:0;z-index:100;gap:12px;flex-wrap:wrap;}}
  .header-left{{display:flex;align-items:center;gap:10px;}}
  .brand-name{{font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:800;color:var(--cyan);letter-spacing:3px;}}
  .brand-sub{{font-size:0.55rem;color:var(--muted);letter-spacing:2px;}}
  .divider-v{{width:1px;height:28px;background:var(--border);}}
  .header-ticker{{font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;color:var(--accent);}}
  .header-info{{display:flex;flex-direction:column;}}
  .header-name{{font-size:0.7rem;color:var(--muted);}}
  .header-setor{{font-size:0.65rem;color:var(--cyan);}}
  .header-right{{display:flex;align-items:center;gap:12px;}}
  .header-cotacao{{font-family:'Syne',sans-serif;font-size:1.35rem;font-weight:700;color:var(--text);}}
  .header-date{{font-size:0.6rem;color:var(--muted);}}
  .search-bar{{display:flex;align-items:center;gap:6px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:4px 8px;}}
  .search-bar input{{background:transparent;border:none;outline:none;color:var(--text);
    font-family:'JetBrains Mono',monospace;font-size:0.75rem;width:80px;text-transform:uppercase;}}
  .search-bar input::placeholder{{color:var(--muted);}}
  .search-bar button{{background:var(--accent);color:#000;border:none;border-radius:4px;
    padding:3px 8px;cursor:pointer;font-family:'Syne',sans-serif;font-weight:700;font-size:0.65rem;}}
  #search-status{{font-size:0.6rem;color:var(--muted);min-width:70px;}}
  .container{{max-width:1280px;margin:0 auto;padding:10px 14px;display:grid;grid-template-columns:240px 1fr;gap:10px;}}
  .sidebar{{display:flex;flex-direction:column;gap:8px;}}
  .main   {{display:flex;flex-direction:column;gap:8px;}}
  .section{{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:10px;}}
  .section-title{{font-family:'Syne',sans-serif;font-size:0.6rem;font-weight:700;
    letter-spacing:2px;text-transform:uppercase;color:var(--muted);
    margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border);
    display:flex;align-items:center;gap:8px;flex-wrap:wrap;}}
  .score-main{{background:linear-gradient(135deg,var(--bg2),#161920);
    border:1px solid var(--accent);border-radius:8px;padding:12px;text-align:center;}}
  .score-number{{font-family:'Syne',sans-serif;font-size:2.6rem;font-weight:800;color:var(--accent);line-height:1;}}
  .score-label{{font-size:0.65rem;font-weight:700;color:var(--accent);letter-spacing:3px;margin-top:2px;}}
  .score-sub{{font-size:0.6rem;color:var(--muted);}}
  .score-cats{{display:flex;flex-direction:column;gap:6px;}}
  .score-cat-row{{display:grid;grid-template-columns:65px 1fr 42px;align-items:center;gap:6px;font-size:0.65rem;}}
  .score-cat-name{{color:var(--muted);}}
  .score-bar-track{{background:var(--bg3);border-radius:3px;height:5px;overflow:hidden;border:1px solid var(--border);}}
  .score-bar-fill{{height:100%;border-radius:3px;}}
  .score-cat-val{{text-align:right;color:var(--text);font-weight:600;font-size:0.6rem;}}
  .score-cat-note{{font-size:0.55rem;color:var(--cyan);grid-column:2/4;margin-top:-3px;}}
  .ind-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:6px;}}
  .ind-card{{background:var(--bg3);border-radius:6px;padding:6px 8px;border-left:2px solid var(--border);}}
  .ind-card.green {{border-left-color:var(--green);}} .ind-card.yellow{{border-left-color:var(--yellow);}} .ind-card.red{{border-left-color:var(--red);}}
  .ind-label{{font-size:0.55rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;}}
  .ind-value{{font-size:0.88rem;font-weight:700;color:var(--text);margin-top:1px;}}
  .ind-card.green .ind-value{{color:var(--green);}} .ind-card.yellow .ind-value{{color:var(--yellow);}} .ind-card.red .ind-value{{color:var(--red);}}
  .val-status{{font-family:'Syne',sans-serif;font-size:0.85rem;font-weight:700;margin-bottom:8px;}}
  .vbar-wrap{{margin:6px 0 10px;}}
  .vbar-track{{position:relative;height:12px;background:var(--bg3);border-radius:6px;border:1px solid var(--border);overflow:visible;}}
  .vbar-fill{{height:100%;border-radius:6px;opacity:0.7;}}
  .vbar-marker{{position:absolute;top:-4px;width:2px;height:20px;border-radius:2px;}}
  .vbar-marker.justo{{background:var(--cyan);}} .vbar-marker.teto{{background:var(--yellow);}}
  .vbar-cotacao{{position:absolute;top:-16px;transform:translateX(-50%);font-size:0.75rem;color:var(--text);}}
  .val-items{{display:flex;gap:14px;flex-wrap:wrap;margin-top:4px;}}
  .val-item{{display:flex;flex-direction:column;gap:1px;}}
  .val-item span{{font-size:0.55rem;color:var(--muted);}} .val-item strong{{font-size:0.8rem;color:var(--text);}}
  .sim-controls{{display:flex;align-items:center;gap:5px;margin-left:auto;flex-wrap:wrap;}}
  .sim-controls input{{background:var(--bg3);border:1px solid var(--border);color:var(--text);
    border-radius:4px;padding:2px 5px;font-family:'JetBrains Mono',monospace;font-size:0.65rem;width:55px;}}
  .sim-controls button{{background:var(--accent);color:#000;border:none;border-radius:4px;
    padding:2px 7px;cursor:pointer;font-family:'Syne',sans-serif;font-weight:700;font-size:0.6rem;}}
  #sim-status{{font-size:0.6rem;color:var(--yellow);}}
  .sim-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px;}}
  .sim-card{{background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);text-align:center;}}
  .sim-card.highlight{{border-color:var(--green);background:rgba(0,255,136,0.05);}}
  .sim-label{{font-size:0.6rem;color:var(--muted);margin-bottom:4px;}}
  .sim-value{{font-size:0.95rem;font-weight:700;color:var(--text);}}
  .sim-ret{{font-size:0.75rem;font-weight:600;margin-top:2px;}}
  .sim-sub{{font-size:0.55rem;color:var(--muted);margin-top:2px;}}
  .sim-meta{{font-size:0.58rem;color:var(--muted);margin-bottom:10px;padding:4px 8px;
    background:var(--bg3);border-radius:4px;border:1px solid var(--border);}}
  .div-chart{{display:flex;align-items:flex-end;gap:3px;height:80px;padding:0 2px;overflow-x:auto;}}
  .div-bar-wrap{{display:flex;flex-direction:column;align-items:center;gap:1px;min-width:40px;flex-shrink:0;}}
  .div-bar-val{{font-size:0.5rem;color:var(--muted);white-space:nowrap;}}
  .div-bar-col{{width:24px;height:50px;display:flex;align-items:flex-end;}}
  .div-bar-fill{{width:100%;border-radius:2px 2px 0 0;min-height:2px;}}
  .div-bar-date{{font-size:0.5rem;color:var(--muted);}} .div-bar-tipo{{font-size:0.5rem;font-weight:700;}}
  .osc-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(85px,1fr));gap:5px;}}
  .osc-item{{background:var(--bg3);border-radius:5px;padding:4px 6px;display:flex;justify-content:space-between;align-items:center;border:1px solid var(--border);}}
  .osc-label{{font-size:0.6rem;color:var(--muted);}} .osc-val{{font-size:0.75rem;font-weight:700;}}
  .oport-section{{border-color:rgba(0,255,136,0.3);}} .band-section{{border-color:rgba(255,68,85,0.3);}}
  .oport-section .section-title{{color:var(--green);}} .band-section .section-title{{color:var(--red);}}
  .oport-item,.band-item{{list-style:none;padding:4px 7px;border-radius:4px;margin-bottom:3px;font-size:0.7rem;}}
  .oport-item{{background:rgba(0,255,136,0.07);color:var(--green);}}
  .band-item{{background:rgba(255,68,85,0.07);color:var(--red);}}
  .class-final{{background:linear-gradient(135deg,rgba(255,255,255,0.02),var(--bg2));
    border:1px solid var(--accent);border-radius:8px;padding:14px;text-align:center;grid-column:1/-1;}}
  .class-txt{{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:800;color:var(--accent);letter-spacing:1px;}}
  .class-sub{{font-size:0.6rem;color:var(--muted);margin-top:4px;}}
  .tec-grid{{display:grid;grid-template-columns:1fr 1fr;gap:6px;}}
  .footer{{text-align:center;padding:10px;font-size:0.55rem;color:var(--muted);border-top:1px solid var(--border);}}
  @media(max-width:860px){{.container{{grid-template-columns:1fr;}}.sim-grid{{grid-template-columns:1fr;}}.header{{flex-direction:column;align-items:flex-start;}}}}
</style>
</head>
<body>
<div class="header">
  <div class="header-left">
    <div><div class="brand-name">⚛ QUANTTECH</div><div class="brand-sub">TRADING SOLUTIONS</div></div>
    <div class="divider-v"></div>
    <div class="header-ticker">{ticker_clean}</div>
    <div class="header-info">
      <div class="header-name">{dados.get("nome","") or ""}</div>
      <div class="header-setor">{dados.get("setor","") or ""}{(" · "+dados.get("subsetor","")) if dados.get("subsetor") else ""}</div>
    </div>
  </div>
  <div class="header-right">
    <div><div class="header-cotacao">R$ {fmt(dados.get("cotacao"))}</div><div class="header-date">{now}</div></div>
    <div class="search-bar">
      <input type="text" id="ticker-input" placeholder="Ex: VALE3" maxlength="10" onkeydown="if(event.key==='Enter') buscarTicker()">
      <button onclick="buscarTicker()">ANALISAR</button>
    </div>
    <div id="search-status"></div>
  </div>
</div>
<div class="container">
  <div class="sidebar">
    <div class="score-main">
      <div class="score-number">{score_total}</div><div class="score-sub">/100</div>
      <div class="score-label">{slabel}</div>
    </div>
    <div class="section">
      <div class="section-title">Score por Categoria</div>
      <div class="score-cats">
        <div class="score-cat-row"><div class="score-cat-name">Qualidade</div>
          <div class="score-bar-track">{barra(scores["qualidade"],40,"#4da6ff")}</div>
          <div class="score-cat-val">{scores["qualidade"]}/40</div></div>
        <div class="score-cat-row"><div class="score-cat-name">Valuation</div>
          <div class="score-bar-track">{barra(scores["valuation"],30,"#00ff88")}</div>
          <div class="score-cat-val">{scores["valuation"]}/30</div>
          {"<div class='score-cat-note'>📈 PEG aplicado</div>" if scores.get("empresa_crescimento") else ""}</div>
        <div class="score-cat-row"><div class="score-cat-name">Crescimento</div>
          <div class="score-bar-track">{barra(scores["crescimento"],20,"#ffd700")}</div>
          <div class="score-cat-val">{scores["crescimento"]}/20</div></div>
        <div class="score-cat-row"><div class="score-cat-name">Solidez</div>
          <div class="score-bar-track">{barra(scores["solidez"],10,"#00e5ff")}</div>
          <div class="score-cat-val">{scores["solidez"]}/10</div>
          {"<div class='score-cat-note'>🏦 Critério Bancário</div>" if eh_banco else ""}</div>
      </div>
    </div>
    {oport_html}{band_html}{osc_html}{tec_html}
  </div>
  <div class="main">
    <div class="section"><div class="section-title">📊 Múltiplos</div><div class="ind-grid">
      {card("P/L",fmt(dados.get("pl"),1),cor(dados.get("pl"),0,10,True) if dados.get("pl") and dados["pl"]>0 else "red")}
      {card("P/VP",fmt(dados.get("pvp"),2),cor(dados.get("pvp"),0,1.5,True) if dados.get("pvp") else "neutral")}
      {card("PSR",fmt(dados.get("psr"),2),cor(dados.get("psr"),0,2,True) if dados.get("psr") else "neutral")}
      {card("P/EBIT",fmt(dados.get("p_ebit"),1),cor(dados.get("p_ebit"),0,10,True) if dados.get("p_ebit") else "neutral")}
      {card("EV/EBITDA",fmt(dados.get("ev_ebitda"),1),cor(dados.get("ev_ebitda"),0,6,True) if dados.get("ev_ebitda") else "neutral")}
      {card("EV/EBIT",fmt(dados.get("ev_ebit"),1),cor(dados.get("ev_ebit"),0,12,True) if dados.get("ev_ebit") else "neutral")}
      {card("LPA",f"R$ {fmt(dados.get('lpa'),2)}","neutral")}
      {card("VPA",f"R$ {fmt(dados.get('vpa'),2)}","neutral")}
    </div></div>
    <div class="section"><div class="section-title">💎 Rentabilidade & Margens</div><div class="ind-grid">
      {card("ROE",fmt(dados.get("roe"),1,"%"),cor(dados.get("roe"),20,10))}
      {card("ROIC",fmt(dados.get("roic"),1,"%"),cor(dados.get("roic"),15,10))}
      {card("EBIT/Ativo",fmt(dados.get("ebit_ativo"),1,"%"),cor(dados.get("ebit_ativo"),8,4))}
      {card("M. Bruta",fmt(dados.get("margem_bruta"),1,"%"),cor(dados.get("margem_bruta"),30,15))}
      {card("M. EBIT",fmt(dados.get("margem_ebit"),1,"%"),cor(dados.get("margem_ebit"),15,8))}
      {card("M. Líquida",fmt(dados.get("margem_liquida"),1,"%"),cor(dados.get("margem_liquida"),10,5))}
    </div></div>
    {"<div class='section'><div class='section-title'>🏦 Endividamento & Liquidez</div><div class='ind-grid'>" +
      card("Dív.Br/Patrim",fmt(dados.get("divida_bruta_patrim"),2),cor(dados.get("divida_bruta_patrim"),0,0.5,True)) +
      card("Dív.Líq/EBITDA",fmt(dados.get("divida_liquida_ebitda"),1,"x"),cor(dados.get("divida_liquida_ebitda"),0,2,True)) +
      card("Liquidez Corr.",fmt(dados.get("liquidez_corrente"),2),cor(dados.get("liquidez_corrente"),2,1.5)) +
      card("Giro Ativos",fmt(dados.get("giro_ativos"),2),cor(dados.get("giro_ativos"),0.8,0.4)) +
     "</div></div>"
     if not eh_banco else
     "<div class='section'><div class='section-title'>🏦 Endividamento & Liquidez</div><div style='color:#4da6ff;font-size:0.7rem;padding:4px 0'>Empresa financeira — métricas de dívida/liquidez não aplicáveis.</div></div>"}
    <div class="section"><div class="section-title">📈 Crescimento & Dividendos</div><div class="ind-grid">
      {card("Cresc. 5a",fmt(dados.get("crescimento_receita"),1,"%"),cor(dados.get("crescimento_receita"),20,10))}
      {card("Div. Yield",fmt(dados.get("div_yield"),1,"%"),cor(dados.get("div_yield"),6,3))}
      {card("Val. Mercado",fmt_bi(dados.get("valor_mercado")),"neutral")}
      {card("Val. Firma",fmt_bi(dados.get("valor_firma")),"neutral")}
      {card("Lucro Líq.",fmt_bi(dados.get("lucro_liquido")),"green" if (dados.get("lucro_liquido") or 0)>0 else "red")}
    </div></div>
    {val_html}
    {sim_html}
    <div class="class-final">
      <div class="class-txt">{ctxt}</div>
      <div class="class-sub">Score {score_total}/100 · {dados.get("setor","") or ""} · {now}</div>
    </div>
  </div>
</div>
<div class="footer">⚛️ QUANTTECH · Dados: Fundamentus + Yahoo Finance · Não constitui recomendação de investimento</div>
<script>
function buscarTicker() {{
  const t = document.getElementById('ticker-input').value.trim().toUpperCase();
  if (!t) {{ alert('Digite um ticker!'); return; }}
  const st = document.getElementById('search-status');
  st.textContent = '⏳ ' + t + '...';
  st.style.color = '#ffd700';
  window.location.href = '/analisar?ticker=' + t;
}}

function recalcularSim() {{
  const valor = document.getElementById('sim-valor').value;
  const ano   = document.getElementById('sim-ano').value;
  const st    = document.getElementById('sim-status');
  if (!valor || !ano) return;
  st.textContent = '⏳ calculando...';
  fetch('/simular?ticker={ticker_clean}&valor=' + valor + '&ano=' + ano)
    .then(r => r.json())
    .then(d => {{
      st.textContent = '';
      if (d.erro) {{ st.textContent = '❌ ' + d.erro; return; }}
      document.getElementById('sim-content').innerHTML = d.html;
    }})
    .catch(() => {{ st.textContent = '❌ erro'; }});
}}
</script>
</body></html>'''


# ══════════════════════════════════════════════════════════════
#  FLASK APP — SERVIDOR WEB
# ══════════════════════════════════════════════════════════════

app = Flask(__name__)

# Controle de usuários simultâneos
_lock_usuarios = threading.Lock()
_usuarios_ativos = 0
MAX_USUARIOS = 30

PAGINA_INICIO = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>⚛️ QUANTTECH — Análise de Ações Brasileiras</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;700;800&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:#0a0c10;color:#e8eaf0;font-family:'JetBrains Mono',monospace;
    min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;}}
  .logo{{font-family:'Syne',sans-serif;font-size:3rem;font-weight:800;color:#00e5ff;
    letter-spacing:4px;margin-bottom:6px;}}
  .sub{{font-size:0.7rem;color:#6b7280;letter-spacing:3px;margin-bottom:48px;}}
  .tagline{{font-size:1rem;color:#e8eaf0;margin-bottom:32px;text-align:center;}}
  .search-wrap{{display:flex;gap:10px;align-items:center;}}
  .search-wrap input{{background:#111318;border:1px solid #2a2d36;color:#e8eaf0;
    border-radius:8px;padding:12px 18px;font-family:'JetBrains Mono',monospace;
    font-size:1rem;width:220px;text-transform:uppercase;outline:none;
    transition:border 0.2s;}}
  .search-wrap input:focus{{border-color:#00e5ff;}}
  .search-wrap input::placeholder{{color:#6b7280;text-transform:none;}}
  .search-wrap button{{background:#00e5ff;color:#000;border:none;border-radius:8px;
    padding:12px 24px;cursor:pointer;font-family:'Syne',sans-serif;font-weight:800;
    font-size:0.9rem;letter-spacing:1px;transition:opacity 0.2s;}}
  .search-wrap button:hover{{opacity:0.85;}}
  .hint{{font-size:0.65rem;color:#6b7280;margin-top:16px;}}
  .footer{{position:fixed;bottom:16px;font-size:0.6rem;color:#6b7280;}}
  #loading{{display:none;margin-top:24px;text-align:center;}}
  .spinner{{width:32px;height:32px;border:3px solid #1a1d24;border-top-color:#00e5ff;
    border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 12px;}}
  @keyframes spin{{to{{transform:rotate(360deg);}}}}
  .loading-txt{{font-size:0.75rem;color:#6b7280;}}
</style>
</head>
<body>
<div class="logo">⚛ QUANTTECH</div>
<div class="sub">TRADING SOLUTIONS</div>
<div class="tagline">Análise fundamentalista de ações brasileiras</div>
<div class="search-wrap">
  <input type="text" id="ticker" placeholder="Ex: PETR4, VALE3, ITUB4" maxlength="10"
         onkeydown="if(event.key==='Enter') analisar()">
  <button onclick="analisar()">ANALISAR</button>
</div>
<div class="hint">Digite o ticker da ação e pressione ANALISAR</div>
<div id="loading">
  <div class="spinner"></div>
  <div class="loading-txt" id="loading-txt">Buscando dados... aguarde ~20 segundos</div>
</div>
<div class="footer">Dados: Fundamentus + Yahoo Finance · Não constitui recomendação de investimento</div>
<script>
function analisar() {
  const t = document.getElementById('ticker').value.trim().toUpperCase();
  if (!t) { alert('Digite um ticker!'); return; }
  document.getElementById('loading').style.display = 'block';
  document.getElementById('loading-txt').textContent = 'Analisando ' + t + '... aguarde ~20 segundos';
  window.location.href = '/analisar?ticker=' + t;
}
</script>
</body></html>'''

PAGINA_SOBRECARGA = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>⚛️ QUANTTECH — Sistema Sobrecarregado</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:#0a0c10;color:#e8eaf0;font-family:'Syne',sans-serif;
    min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;}}
  .icon{{font-size:3rem;}}
  .title{{font-size:1.5rem;font-weight:800;color:#ffd700;}}
  .msg{{font-size:0.85rem;color:#6b7280;text-align:center;max-width:360px;line-height:1.8;}}
  a{{color:#00e5ff;text-decoration:none;font-size:0.8rem;}}
  a:hover{{opacity:0.8;}}
</style>
</head>
<body>
<div class="icon">⚡</div>
<div class="title">Sistema Sobrecarregado</div>
<div class="msg">O sistema está com muitos usuários simultâneos no momento.<br>Por favor, tente novamente em alguns minutos.</div>
<a href="/">← Voltar ao início</a>
</body></html>'''


@app.route('/')
def index():
    return Response(PAGINA_INICIO, mimetype='text/html; charset=utf-8')


@app.route('/analisar')
def analisar_route():
    global _usuarios_ativos
    ticker = request.args.get('ticker', '').upper().strip()
    if not ticker:
        return Response(PAGINA_INICIO, mimetype='text/html; charset=utf-8')

    with _lock_usuarios:
        if _usuarios_ativos >= MAX_USUARIOS:
            return Response(PAGINA_SOBRECARGA, mimetype='text/html; charset=utf-8')
        _usuarios_ativos += 1

    try:
        dados = buscar_dados_fundamentus(ticker)
        if not dados:
            return Response(f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
            <style>body{{background:#0a0c10;color:#e8eaf0;font-family:monospace;
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              min-height:100vh;gap:16px;}}
              a{{color:#00e5ff;}}</style></head>
            <body><h2>❌ Ticker "{ticker}" não encontrado</h2>
            <p style="color:#6b7280">Verifique se o ticker está correto (ex: PETR4, VALE3, ITUB4)</p>
            <a href="/">← Voltar</a></body></html>''',
            mimetype='text/html; charset=utf-8')

        scores  = calcular_score_consolidado(dados)
        insights = gerar_alertas_inteligentes(dados, ticker)

        ticker_yf = ticker if '.SA' in ticker else f'{ticker}.SA'
        variacao_3m = None
        acima_ema50 = None
        try:
            acao = yf.Ticker(ticker_yf)
            hist_semanal = acao.history(period="6mo", interval="1wk")
            if not hist_semanal.empty:
                fechamento = hist_semanal["Close"].iloc[-1]
                ema50 = hist_semanal["Close"].ewm(span=50).mean().iloc[-1]
                acima_ema50 = fechamento > ema50
                hist_3m = acao.history(period="3mo")
                if not hist_3m.empty:
                    variacao_3m = ((hist_3m["Close"].iloc[-1] - hist_3m["Close"].iloc[0]) / hist_3m["Close"].iloc[0]) * 100
        except: pass

        preco_justo = preco_teto = None
        if all([dados.get('lpa'), dados.get('crescimento_receita'), dados.get('vpa'), dados.get('cotacao')]):
            preco_justo, _ = calcular_preco_justo_graham(dados['lpa'], dados['crescimento_receita'], dados['vpa'], scores['total'])
            preco_teto, _  = calcular_preco_teto(dados['lpa'], dados['vpa'], scores['qualidade'])

        sim = simulacao_investimento(ticker_yf)

        html = gerar_html_relatorio(ticker, dados, scores, insights, sim,
                                    preco_justo=preco_justo, preco_teto=preco_teto,
                                    variacao_3m=variacao_3m, acima_ema50=acima_ema50)
        return Response(html, mimetype='text/html; charset=utf-8')

    except Exception as e:
        print(f"[ERRO] /analisar {ticker}: {traceback.format_exc()}")
        return Response(f'<h2>Erro ao analisar {ticker}: {e}</h2><a href="/">Voltar</a>',
                        mimetype='text/html; charset=utf-8')
    finally:
        with _lock_usuarios:
            _usuarios_ativos = max(0, _usuarios_ativos - 1)


@app.route('/simular')
def simular_route():
    ticker = request.args.get('ticker', '').upper().strip()
    valor  = float(request.args.get('valor', 1000))
    ano    = int(request.args.get('ano', 2019))
    ticker_yf = ticker if '.SA' in ticker else f'{ticker}.SA'
    try:
        sim = simulacao_investimento(ticker_yf, valor_inicial=valor, ano_inicio=ano)
        if not sim:
            return jsonify({'erro': 'Dados insuficientes'}), 400
        gc = '#00ff88' if sim['ganho_reinvestimento']>0 else '#ff4444'
        cs = '#00ff88' if sim['retorno_sem']>0 else '#ff4444'
        chart_bars = ''
        if sim['historico_dividendos']:
            max_r = max(d['recebido'] for d in sim['historico_dividendos'])
            for d in sim['historico_dividendos']:
                h = (d['recebido']/max_r)*100 if max_r>0 else 0
                tipo = 'JCP' if d['valor_unit']<0.05 else 'DIV'
                ct   = '#ffd700' if tipo=='JCP' else '#00ff88'
                chart_bars += f'<div class="div-bar-wrap"><div class="div-bar-val">R${d["recebido"]:.0f}</div><div class="div-bar-col"><div class="div-bar-fill" style="height:{h:.0f}%;background:{ct}"></div></div><div class="div-bar-date">{d["data"]}</div><div class="div-bar-tipo" style="color:{ct}">{tipo}</div></div>'
        html = f'''<div class="sim-grid">
          <div class="sim-card"><div class="sim-label">📦 Sem reinvestimento</div>
            <div class="sim-value">R$ {sim["valor_sem_reinv_total"]:,.2f}</div>
            <div class="sim-ret" style="color:{cs}">{sim["retorno_sem"]:+.1f}%</div>
            <div class="sim-sub">CAGR {sim["cagr_sem"]:.1f}% a.a.</div></div>
          <div class="sim-card highlight"><div class="sim-label">🔄 Com reinvestimento</div>
            <div class="sim-value">R$ {sim["valor_com_reinv"]:,.2f}</div>
            <div class="sim-ret" style="color:#00ff88">{sim["retorno_com"]:+.1f}%</div>
            <div class="sim-sub">CAGR {sim["cagr_com"]:.1f}% a.a.</div></div>
          <div class="sim-card"><div class="sim-label">⚡ Ganho do reinvestimento</div>
            <div class="sim-value" style="color:{gc}">R$ {sim["ganho_reinvestimento"]:,.2f}</div>
            <div class="sim-ret" style="color:{gc}">{sim["retorno_com"]-sim["retorno_sem"]:+.1f}%</div>
            <div class="sim-sub">{sim["num_dividendos"]} pagamentos · {sim["acoes_iniciais"]:.1f}→{sim["acoes_com_reinv"]:.1f} ações</div></div>
        </div>
        <div class="sim-meta">Entrada {sim["data_entrada"]} · R$ {sim["preco_entrada"]:.2f} → R$ {sim["preco_atual"]:.2f} hoje</div>
        <div class="div-chart">{chart_bars}</div>'''
        return jsonify({'ok': True, 'html': html})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'usuarios_ativos': _usuarios_ativos})


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
