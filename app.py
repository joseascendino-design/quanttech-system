"""
QUANTTECH VALOR JUSTO
Execute: python app.py
Acesse:  http://localhost:8765
Sem necessidade de chave de API!
"""

import json, re, threading, webbrowser, math
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen, Request
from urllib.error import URLError

# ── Compatibilidade com Gunicorn/Railway ──────────────────────────
# Railway detecta automaticamente e tenta usar Gunicorn (WSGI)
# Este objeto garante que o servidor HTTPServer seja iniciado corretamente
class _WSGICompat:
    """Adapter mínimo para satisfazer Gunicorn e iniciar nosso HTTPServer."""
    def __init__(self):
        self._started = False
    def __call__(self, environ, start_response):
        if not self._started:
            self._started = True
            t = threading.Thread(target=_iniciar_http, daemon=True)
            t.start()
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'QuantTech iniciando...']

def _iniciar_http():
    import time, os
    time.sleep(1)
    port = int(os.environ.get("PORT", 8765))
    srv = HTTPServer(("0.0.0.0", port), Handler)
    srv.serve_forever()

app = _WSGICompat()
# ─────────────────────────────────────────────────────────────────

import os
PORT = int(os.environ.get("PORT", 8765))


HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuantTech · Valor Justo</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{
  --cream:#f4f7fc;--paper:#ffffff;--ink:#0a0f1e;--ink2:#1e2a3a;
  --ink3:#4a6080;--ink4:#8a9ab0;--gold:#c8960c;--gold2:#e8b420;
  --green:#0d5c2e;--green2:#22c55e;--red:#7a1010;--red2:#ef4444;
  --blue:#0047cc;--blue2:#3b82f6;--border:#dde4ef;--shadow:rgba(10,15,30,0.08);
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--cream);color:var(--ink);font-family:'DM Sans',sans-serif;min-height:100vh}
body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 70% 40% at 10% 0%,rgba(0,71,204,.06),transparent 60%),
    radial-gradient(ellipse 50% 35% at 90% 100%,rgba(13,92,46,.04),transparent 60%)}
.page{max-width:740px;margin:0 auto;padding:28px 16px 80px;position:relative;z-index:1}

/* ── Masthead ── */
.masthead{text-align:center;padding:36px 0 28px;margin-bottom:32px;position:relative}
.masthead::after{content:'';position:absolute;bottom:0;left:50%;transform:translateX(-50%);
  width:100px;height:3px;background:linear-gradient(90deg,var(--blue2),var(--gold2));border-radius:2px}
.brand-row{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;margin-bottom:12px}
.brand-icon{width:54px;height:54px;
  background:linear-gradient(135deg,#0047cc,#3b82f6);
  border-radius:14px;display:flex;align-items:center;justify-content:center;
  font-size:16px;font-family:'DM Mono',monospace;font-weight:700;color:#fff;
  letter-spacing:-1px;box-shadow:0 4px 20px rgba(0,71,204,.25)}
.brand-text{text-align:left}
.brand-quant{font-family:'DM Mono',monospace;font-size:13px;letter-spacing:3px;
  color:var(--blue2);font-weight:800;display:flex;align-items:center;gap:8px}
.brand-star{font-size:16px;line-height:1}
.brand-trading{color:var(--ink4);font-weight:400;letter-spacing:1px;font-size:11px}
.brand-title{font-family:'DM Serif Display',serif;font-size:clamp(28px,6vw,40px);
  line-height:1;color:var(--ink);letter-spacing:-1px;text-align:center}
.brand-title em{color:var(--gold);font-style:italic}
.brand-sub{font-size:13px;color:var(--ink3);margin-top:10px;font-weight:300}
.live-badge{display:inline-flex;align-items:center;gap:6px;
  background:var(--ink);color:#fff;border-radius:20px;
  padding:5px 14px;margin-top:12px;
  font-family:'DM Mono',monospace;font-size:10px;letter-spacing:2px}
.live-dot{width:6px;height:6px;background:var(--green2);border-radius:50%;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.6)}}

/* ── Search ── */
.search-card{background:var(--ink);border-radius:12px 12px 0 0;padding:28px 24px;
  margin-bottom:0;box-shadow:0 12px 40px rgba(10,15,30,.2);position:relative;overflow:hidden}
.search-card::before{content:'';position:absolute;top:-50px;right:-50px;
  width:200px;height:200px;pointer-events:none;
  background:radial-gradient(circle,rgba(59,130,246,.15),transparent 70%)}
.search-card::after{content:'';position:absolute;bottom:-40px;left:-40px;
  width:160px;height:160px;pointer-events:none;
  background:radial-gradient(circle,rgba(232,180,32,.1),transparent 70%)}
.s-label{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;
  color:rgba(255,255,255,.4);margin-bottom:12px}
.s-row{display:flex;gap:10px;position:relative;z-index:1}
.ticker-input{flex:1;background:rgba(255,255,255,.07);
  border:1px solid rgba(255,255,255,.15);border-radius:8px;
  padding:14px 20px;font-family:'DM Serif Display',serif;font-size:28px;
  color:#fff;outline:none;letter-spacing:3px;text-transform:uppercase;
  transition:border-color .2s,box-shadow .2s}
.ticker-input::placeholder{color:rgba(255,255,255,.2);font-size:20px;letter-spacing:1px}
.ticker-input:focus{border-color:var(--gold2);box-shadow:0 0 0 3px rgba(232,180,32,.15)}
.btn-analisar{background:linear-gradient(135deg,var(--gold),var(--gold2));
  color:var(--ink);border:none;border-radius:8px;
  padding:14px 28px;font-family:'DM Serif Display',serif;font-size:18px;
  cursor:pointer;transition:all .2s;white-space:nowrap;
  box-shadow:0 4px 16px rgba(200,150,12,.3)}
.btn-analisar:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(200,150,12,.4)}
.btn-analisar:disabled{opacity:.4;cursor:not-allowed;transform:none;box-shadow:none}
.s-hint{margin-top:10px;font-family:'DM Mono',monospace;font-size:11px;
  color:rgba(255,255,255,.3);letter-spacing:1px;position:relative;z-index:1}

/* ── Loading ── */
.loading{display:none;background:var(--paper);border:1px solid var(--border);
  border-radius:12px;padding:48px 24px;margin-bottom:24px;text-align:center;
  box-shadow:0 4px 20px var(--shadow)}
.loading.on{display:block}
.spinner{width:48px;height:48px;border:3px solid var(--border);
  border-top-color:var(--blue2);border-radius:50%;
  animation:spin .8s linear infinite;margin:0 auto 20px}
@keyframes spin{to{transform:rotate(360deg)}}
.l-title{font-family:'DM Serif Display',serif;font-size:22px;color:var(--ink2);margin-bottom:6px}
.l-sub{font-size:13px;color:var(--ink4)}

/* ── Error ── */
.error{display:none;background:#fff5f5;border:1.5px solid var(--red2);
  border-radius:10px;padding:18px 20px;margin-bottom:20px;
  color:var(--red);font-size:13px;line-height:1.6}
.error.on{display:block}

/* ── Dados card ── */
.dados-card{display:none;background:var(--paper);border:1px solid var(--border);
  border-radius:12px;overflow:hidden;margin-bottom:20px;
  animation:up .4s ease;box-shadow:0 4px 20px var(--shadow)}
.dados-card.on{display:block}
@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
.dados-header{display:flex;align-items:center;justify-content:space-between;
  padding:18px 22px;background:linear-gradient(135deg,var(--ink),var(--ink2));
  border-bottom:1px solid var(--border)}
.dh-left{display:flex;align-items:center;gap:12px}
.dh-icon{width:40px;height:40px;background:linear-gradient(135deg,var(--blue),var(--blue2));
  border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px}
.d-ticker{font-family:'DM Serif Display',serif;font-size:24px;color:#fff}
.d-empresa{font-size:11px;color:rgba(255,255,255,.5);margin-top:2px;font-weight:300}
.fonte-tag{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1px;
  background:rgba(255,255,255,.1);color:rgba(255,255,255,.6);
  padding:4px 10px;border-radius:20px;border:1px solid rgba(255,255,255,.15)}
.dados-grid{display:grid;grid-template-columns:repeat(3,1fr)}
.dado{padding:16px 18px;border-right:1px solid var(--border);border-bottom:1px solid var(--border)}
.dado:nth-child(3n){border-right:none}
.dado:nth-last-child(-n+3){border-bottom:none}
.d-lbl{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:2px;
  color:var(--ink4);margin-bottom:5px}
.d-val{font-family:'DM Serif Display',serif;font-size:20px;color:var(--ink)}
.pos{color:var(--green)}.neg{color:var(--red2)}.gld{color:var(--gold)}

/* ── Resultado ── */
#result{display:none}

.verdict{border-radius:12px;padding:28px 26px;margin-bottom:20px;
  position:relative;overflow:hidden;animation:up .4s ease;
  box-shadow:0 4px 20px var(--shadow)}
.verdict.buy{background:linear-gradient(135deg,#f0faf4,#e8f8f0);border:2px solid var(--green2)}
.verdict.hold{background:linear-gradient(135deg,#fffbf0,#fff8e8);border:2px solid var(--gold2)}
.verdict.avoid{background:linear-gradient(135deg,#fff5f5,#ffeaea);border:2px solid var(--red2)}
.v-eye{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;margin-bottom:8px}
.verdict.buy .v-eye{color:var(--green)}.verdict.hold .v-eye{color:var(--gold)}.verdict.avoid .v-eye{color:var(--red)}
.v-title{font-family:'DM Serif Display',serif;font-size:clamp(22px,5vw,34px);
  line-height:1.1;margin-bottom:12px}
.verdict.buy .v-title{color:var(--green)}.verdict.hold .v-title{color:var(--gold)}.verdict.avoid .v-title{color:var(--red)}
.v-text{font-size:14px;color:var(--ink2);line-height:1.7;font-weight:300}
.v-score{position:absolute;top:20px;right:24px;font-family:'DM Serif Display',serif;
  font-size:72px;opacity:.07;line-height:1}

/* ── Pills ── */
.pills{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px;animation:up .4s .06s ease both}
.pill{flex:1;min-width:110px;background:var(--paper);border:1px solid var(--border);
  border-radius:10px;padding:14px 12px;text-align:center;
  box-shadow:0 2px 8px var(--shadow)}
.p-lbl{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:2px;
  color:var(--ink4);margin-bottom:5px}
.p-val{font-family:'DM Serif Display',serif;font-size:22px}
.p-sub{font-size:10px;color:var(--ink4);margin-top:2px}

/* ── Gauge ── */
.gauge-card{background:var(--paper);border:1px solid var(--border);border-radius:12px;
  padding:22px;margin-bottom:20px;animation:up .4s .1s ease both;
  box-shadow:0 2px 8px var(--shadow)}
.g-lbl{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;
  color:var(--ink3);margin-bottom:16px}
.g-track{height:12px;background:var(--border);border-radius:12px;
  position:relative;margin-bottom:10px}
.g-fill{height:100%;border-radius:12px;
  background:linear-gradient(90deg,var(--red2),var(--gold2),var(--green2));
  transition:width .9s cubic-bezier(.4,0,.2,1)}
.g-pin{position:absolute;top:-5px;width:22px;height:22px;
  background:var(--ink);border:3px solid white;border-radius:50%;
  transform:translateX(-50%);transition:left .9s cubic-bezier(.4,0,.2,1);
  box-shadow:0 2px 8px var(--shadow)}
.g-labs{display:flex;justify-content:space-between;
  font-family:'DM Mono',monospace;font-size:9px;color:var(--ink4);letter-spacing:1px}

/* ── Preço Justo ── */
.preco-card{background:linear-gradient(135deg,var(--ink),var(--ink2));
  color:#fff;border-radius:12px;padding:26px;margin-bottom:20px;
  animation:up .4s .14s ease both;box-shadow:0 6px 24px rgba(10,15,30,.2)}
.pc-lbl{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;
  color:rgba(255,255,255,.4);margin-bottom:18px}
.pc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.pc-il{font-size:9px;font-family:'DM Mono',monospace;letter-spacing:1px;
  color:rgba(255,255,255,.4);margin-bottom:5px}
.pc-iv{font-family:'DM Serif Display',serif;font-size:22px;color:#fff}
.pc-is{font-size:10px;color:rgba(255,255,255,.3);margin-top:3px}
.pc-bottom{border-top:1px solid rgba(255,255,255,.1);
  margin-top:18px;padding-top:18px;
  display:flex;justify-content:space-between;align-items:center}

/* ── Análise Textual ── */
.analise-card{background:var(--paper);border:1px solid var(--border);
  border-radius:12px;overflow:hidden;margin-bottom:20px;
  animation:up .4s .16s ease both;box-shadow:0 2px 8px var(--shadow)}
.analise-hdr{padding:14px 22px;border-bottom:1px solid var(--border);
  background:linear-gradient(135deg,#f8faff,var(--cream));
  font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;color:var(--ink3)}
.analise-body{padding:20px 22px}
.analise-section{margin-bottom:16px}
.analise-section:last-child{margin-bottom:0}
.a-label{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:2px;
  color:var(--blue2);margin-bottom:5px;text-transform:uppercase}
.a-text{font-size:13px;color:var(--ink2);line-height:1.7;font-weight:300}

/* ── Critérios ── */
.crit-card{background:var(--paper);border:1px solid var(--border);
  border-radius:12px;overflow:hidden;margin-bottom:20px;
  animation:up .4s .2s ease both;box-shadow:0 2px 8px var(--shadow)}
.crit-hdr{padding:14px 22px;border-bottom:1px solid var(--border);
  font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;
  color:var(--ink3);background:linear-gradient(135deg,#f8faff,var(--cream))}
.crit{display:flex;align-items:flex-start;gap:12px;
  padding:14px 22px;border-bottom:1px solid var(--border)}
.crit:last-child{border-bottom:none}
.c-ic{width:28px;height:28px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;font-size:13px;
  flex-shrink:0;margin-top:1px}
.c-ic.pass{background:#dcfce7}.c-ic.fail{background:#fee2e2}.c-ic.warn{background:#fef9c3}
.c-body{flex:1}
.c-nome{font-weight:600;font-size:13px;color:var(--ink);margin-bottom:3px}
.c-det{font-size:12px;color:var(--ink3);line-height:1.5;font-weight:300}
.c-badge{font-family:'DM Mono',monospace;font-size:11px;
  padding:3px 10px;border-radius:20px;flex-shrink:0;
  margin-top:2px;white-space:nowrap}
.c-badge.pass{background:#dcfce7;color:var(--green)}
.c-badge.fail{background:#fee2e2;color:var(--red2)}
.c-badge.warn{background:#fef9c3;color:#854d0e}

/* ── Footer ── */
.alerta-politico{background:#1a0a0a;border:1.5px solid var(--red2);border-radius:10px;
  padding:12px 16px;margin-bottom:16px;display:none;animation:up .3s ease}
.alerta-politico.on{display:flex;align-items:flex-start;gap:10px}
.ap-icon{font-size:18px;flex-shrink:0;margin-top:1px}
.ap-body{flex:1}
.ap-title{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:2px;
  color:var(--red2);font-weight:700;margin-bottom:4px}
.ap-items{font-size:12px;color:#ffaaaa;line-height:1.6}

/* ── Abas ── */
.tab-btn:hover:not(.active){background:rgba(255,255,255,.12);color:rgba(255,255,255,.7)}

/* ── Comparação ── */
.ct-rank{font-family:'DM Mono',monospace;font-size:11px;color:var(--ink4);
  width:30px;text-align:center}
.ct-ticker{font-family:'DM Mono',monospace;font-size:13px;font-weight:700;
  color:var(--blue2)}
.ct-empresa{font-size:11px;color:var(--ink3);margin-top:2px;font-weight:300}
.ct-score{font-family:'DM Serif Display',serif;font-size:18px;font-weight:700}
.ct-score.alto{color:var(--green)}
.ct-score.medio{color:var(--gold)}
.ct-score.baixo{color:var(--red2)}
.ct-bar{height:6px;border-radius:6px;margin-top:4px;transition:width .8s ease}
.ct-sinal{font-size:16px}
.ct-preco{font-size:12px;color:var(--ink2)}
.ct-alvo{font-size:11px;color:var(--ink3)}
.ct-desc{font-size:11px;font-weight:600}
.ct-desc.pos{color:var(--green)}
.ct-desc.neg{color:var(--red2)}
.ct-ctx{font-size:18px}
.medal-1{color:#FFD700;font-size:16px}
.medal-2{color:#C0C0C0;font-size:16px}
.medal-3{color:#CD7F32;font-size:16px}

/* ── Contexto Setorial ── */
.contexto-setor{border-radius:10px;padding:14px 18px;margin-bottom:16px;
  animation:up .3s ease;border-left:4px solid}
.contexto-setor.verde{background:#f0faf4;border-color:var(--green2)}
.contexto-setor.amarelo{background:#fffbf0;border-color:var(--gold2)}
.contexto-setor.vermelho{background:#fff5f5;border-color:var(--red2)}
.cs-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.cs-titulo{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:2px;font-weight:700}
.contexto-setor.verde .cs-titulo{color:var(--green)}
.contexto-setor.amarelo .cs-titulo{color:var(--gold)}
.contexto-setor.vermelho .cs-titulo{color:var(--red2)}
.cs-badge{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1px;
  padding:3px 10px;border-radius:20px;font-weight:700}
.contexto-setor.verde .cs-badge{background:#dcfce7;color:var(--green)}
.contexto-setor.amarelo .cs-badge{background:#fef9c3;color:#854d0e}
.contexto-setor.vermelho .cs-badge{background:#fee2e2;color:var(--red2)}
.cs-texto{font-size:12px;line-height:1.7;font-weight:300}
.contexto-setor.verde .cs-texto{color:#1a4a2e}
.contexto-setor.amarelo .cs-texto{color:#4a3a00}
.contexto-setor.vermelho .cs-texto{color:#4a1010}

/* ── Screener ── */
.scr-card{background:var(--ink);border-radius:12px;padding:28px 24px;
  margin-bottom:24px;box-shadow:0 12px 40px rgba(10,15,30,.2);position:relative;overflow:hidden}
.scr-card::before{content:'';position:absolute;top:-50px;right:-50px;
  width:200px;height:200px;pointer-events:none;
  background:radial-gradient(circle,rgba(59,130,246,.15),transparent 70%)}
.scr-label{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;
  color:rgba(255,255,255,.4);margin-bottom:12px}
.scr-textarea{width:100%;background:rgba(255,255,255,.07);
  border:1px solid rgba(255,255,255,.15);border-radius:8px;
  padding:14px 18px;font-family:'DM Mono',monospace;font-size:15px;
  color:#fff;outline:none;letter-spacing:2px;text-transform:uppercase;
  resize:vertical;min-height:80px;transition:border-color .2s}
.scr-textarea::placeholder{color:rgba(255,255,255,.2);font-size:12px;letter-spacing:1px;text-transform:none}
.scr-textarea:focus{border-color:var(--gold2);box-shadow:0 0 0 3px rgba(232,180,32,.15)}
.scr-row{display:flex;gap:10px;margin-top:12px;align-items:center}
.btn-screener{background:linear-gradient(135deg,var(--gold),var(--gold2));
  color:var(--ink);border:none;border-radius:8px;
  padding:12px 24px;font-family:'DM Serif Display',serif;font-size:16px;
  cursor:pointer;transition:all .2s;white-space:nowrap;
  box-shadow:0 4px 16px rgba(200,150,12,.3)}
.btn-screener:hover{transform:translateY(-1px)}
.btn-screener:disabled{opacity:.4;cursor:not-allowed;transform:none}
.scr-progress{font-family:'DM Mono',monospace;font-size:11px;
  color:rgba(255,255,255,.5);flex:1;letter-spacing:1px}

.ranking-card{background:var(--paper);border:1px solid var(--border);
  border-radius:12px;overflow:hidden;margin-bottom:20px;
  animation:up .4s ease;box-shadow:0 4px 20px var(--shadow)}
.ranking-hdr{padding:14px 22px;border-bottom:1px solid var(--border);
  background:linear-gradient(135deg,var(--ink),var(--ink2));
  display:flex;align-items:center;justify-content:space-between}
.rh-title{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;color:rgba(255,255,255,.6)}
.rh-count{font-family:'DM Serif Display',serif;font-size:16px;color:var(--gold2)}

.rk-item{display:grid;grid-template-columns:36px 1fr auto;
  align-items:center;gap:12px;
  padding:14px 22px;border-bottom:1px solid var(--border);
  transition:background .15s;cursor:pointer}
.rk-item:last-child{border-bottom:none}
.rk-item:hover{background:#f8faff}
.rk-num{font-family:'DM Serif Display',serif;font-size:22px;
  color:var(--ink4);text-align:center;line-height:1}
.rk-num.gold{color:#FFD700}.rk-num.silver{color:#A8A9AD}.rk-num.bronze{color:#CD7F32}
.rk-body{flex:1;min-width:0}
.rk-top{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.rk-ticker{font-family:'DM Mono',monospace;font-size:14px;font-weight:700;color:var(--blue2)}
.rk-empresa{font-size:11px;color:var(--ink4);font-weight:300;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px}
.rk-setor{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1px;
  color:var(--ink4);background:var(--cream);padding:2px 8px;border-radius:10px}
.rk-bottom{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.rk-preco{font-size:12px;color:var(--ink2)}
.rk-alvo{font-size:11px;color:var(--ink3)}
.rk-desc{font-size:11px;font-weight:700}
.rk-desc.pos{color:var(--green)}.rk-desc.neg{color:var(--red2)}
.rk-ctx{font-size:14px}
.rk-right{text-align:right;flex-shrink:0}
.rk-score{font-family:'DM Serif Display',serif;font-size:28px;line-height:1}
.rk-score.alto{color:var(--green)}.rk-score.medio{color:var(--gold)}.rk-score.baixo{color:var(--red2)}
.rk-scorelbl{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1px;
  color:var(--ink4);margin-top:2px}
.rk-sinal{font-size:16px;margin-bottom:2px}

.rk-erro{padding:12px 22px;font-size:12px;color:var(--red2);
  font-family:'DM Mono',monospace;border-bottom:1px solid var(--border)}

/* Tabs */
.tabs-nav{display:flex;gap:0;border-radius:0;overflow:hidden;
  background:var(--ink);border-left:none;border-right:none}
.tab-nav-btn{flex:1;padding:13px 16px;font-family:'DM Mono',monospace;font-size:10px;
  letter-spacing:2px;border:none;border-bottom:3px solid transparent;
  cursor:pointer;transition:all .2s;
  background:transparent;color:rgba(255,255,255,.4)}
.tab-nav-btn.active{color:#fff;font-weight:700;
  border-bottom:3px solid var(--gold2);background:rgba(255,255,255,.05)}
.tab-nav-btn:hover:not(.active){color:rgba(255,255,255,.7);background:rgba(255,255,255,.05)}
.tab-content{display:none}
.tabs-wrapper{border:1px solid var(--border);border-radius:0 0 12px 12px;
  background:var(--paper);padding:24px;margin-bottom:24px}

.disc{font-size:11px;color:var(--ink4);line-height:1.8;text-align:center;
  padding:18px;border-top:1px solid var(--border);font-weight:300;
  animation:up .4s .24s ease both}

/* ── Qualitativa ── */
.qual-card{background:var(--paper);border:1px solid var(--border);border-radius:12px;
  overflow:hidden;margin-bottom:20px;animation:up .4s .18s ease both;
  box-shadow:0 2px 8px var(--shadow)}
.qual-hdr{padding:14px 22px;border-bottom:1px solid var(--border);
  background:linear-gradient(135deg,#f0f4ff,#eef2ff);
  display:flex;align-items:center;justify-content:space-between}
.qual-hdr-left{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;color:var(--ink3)}
.qual-score-badge{font-family:'DM Serif Display',serif;font-size:18px;
  background:var(--ink);color:#fff;padding:4px 14px;border-radius:20px}
.qual-loading{padding:32px;text-align:center;color:var(--ink4);font-size:13px}
.qual-spinner{width:28px;height:28px;border:2px solid var(--border);
  border-top-color:var(--blue2);border-radius:50%;
  animation:spin .8s linear infinite;margin:0 auto 12px}
.qual-criterios{padding:0}
.qc{display:flex;align-items:flex-start;gap:14px;
  padding:14px 22px;border-bottom:1px solid var(--border)}
.qc:last-child{border-bottom:none}
.qc-bar-wrap{width:60px;flex-shrink:0;padding-top:4px}
.qc-bar-bg{height:6px;background:var(--border);border-radius:6px;margin-bottom:3px}
.qc-bar-fill{height:100%;border-radius:6px;transition:width .8s ease}
.qc-bar-fill.forte{background:var(--green2)}
.qc-bar-fill.medio{background:var(--gold2)}
.qc-bar-fill.fraco{background:var(--red2)}
.qc-nota{font-family:'DM Mono',monospace;font-size:10px;color:var(--ink4);text-align:center}
.qc-body{flex:1}
.qc-nome{font-weight:600;font-size:13px;color:var(--ink);margin-bottom:2px}
.qc-just{font-size:12px;color:var(--ink3);line-height:1.5;font-weight:300}
.qc-nivel{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:1px;
  padding:2px 8px;border-radius:10px;flex-shrink:0;margin-top:2px}
.qc-nivel.forte{background:#dcfce7;color:var(--green)}
.qc-nivel.medio{background:#fef9c3;color:#854d0e}
.qc-nivel.fraco{background:#fee2e2;color:var(--red2)}
.qual-resumo{padding:16px 22px;background:linear-gradient(135deg,#f8faff,var(--cream));
  border-top:1px solid var(--border);font-size:13px;color:var(--ink2);
  line-height:1.7;font-weight:300}
.score-final-card{background:linear-gradient(135deg,var(--ink),#1a2540);
  border-radius:12px;padding:22px 26px;margin-bottom:20px;
  animation:up .4s .22s ease both;box-shadow:0 6px 24px rgba(10,15,30,.2);
  display:flex;align-items:center;justify-content:space-between;gap:20px}
.sf-label{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;
  color:rgba(255,255,255,.4);margin-bottom:8px}
.sf-score{font-family:'DM Serif Display',serif;font-size:52px;line-height:1}
.sf-sub{font-size:12px;color:rgba(255,255,255,.4);margin-top:4px;font-family:'DM Mono',monospace}
.sf-bars{flex:1;max-width:260px}
.sf-tip{font-size:10px;color:var(--ink4);cursor:help;border:1px solid var(--ink4);
  border-radius:50%;padding:0 3px;line-height:1;vertical-align:middle;
  transition:all .2s}
.sf-tip:hover{color:var(--gold2);border-color:var(--gold2)}

.sf-bar-label{font-size:11px;color:rgba(255,255,255,.5);width:80px;flex-shrink:0;
  font-family:'DM Mono',monospace;letter-spacing:1px}
.sf-bar-track{flex:1;height:8px;background:rgba(255,255,255,.1);border-radius:8px}
.sf-bar-fill{height:100%;border-radius:8px;transition:width .9s ease}
.sf-bar-val{font-size:11px;color:rgba(255,255,255,.6);width:32px;text-align:right;
  font-family:'DM Mono',monospace}

@media(max-width:480px){
  .dados-grid{grid-template-columns:repeat(2,1fr)}
  .pc-grid{grid-template-columns:repeat(2,1fr)}
  .pills{gap:8px}.pill{min-width:90px}
  .brand-row{flex-direction:column;gap:8px}
}
</style>
</head>
<body>
  <!-- Masthead -->
  <div class="masthead">

    <div class="brand-row">
      <div class="brand-text">
        <div class="brand-quant"><span class="brand-star">⚛️</span> QUANTTECH SYSTEM <span class="brand-trading">[Trading Solutions]</span></div>
        <div class="brand-title">Valor<em>Justo</em></div>
      </div>
    </div>
    <div class="brand-sub">Análise fundamentalista automática de ações brasileiras</div>
    <div>
      <span class="live-badge">
        <span class="live-dot"></span>
        DADOS REAIS · B3 · IPCA · IBOV
      </span>
    </div>
  </div>

  <!-- Search -->
  <div class="search-card">
    <div class="s-label">TICKER DA AÇÃO</div>
    <div class="s-row">
      <input class="ticker-input" id="inp" placeholder="PETR4" maxlength="8" autofocus />
      <button class="btn-analisar" id="btn" onclick="analisar()">Analisar →</button>
    </div>
    <div class="s-hint">Ex: PETR4 · VALE3 · ITUB4 · WEGE3 · BBAS3 · SANB4 · TASA4 · EGIE3</div>
  </div>

  


  <div class="error" id="err"></div>

  <!-- Loading simples sem mostrar fontes -->
  <div class="loading" id="load">
    <div class="spinner"></div>
    <div class="l-title">Analisando <span id="loadTicker"></span>...</div>
    <div class="l-sub">Coletando e processando dados fundamentalistas</div>
  </div>

  <!-- Dados -->
  <div class="dados-card" id="dadosCard">
    <div class="dados-header">
      <div class="dh-left">
        <div class="dh-icon">📈</div>
        <div>
          <div class="d-ticker" id="dTicker"></div>
          <div class="d-empresa" id="dEmpresa"></div>
        </div>
      </div>
      <div class="fonte-tag">DADOS REAIS</div>
    </div>
    <div class="dados-grid" id="dGrid"></div>
  </div>

  <!-- Resultado -->
  <div id="result">
    <div class="verdict" id="verdict">
      <div class="v-eye" id="vEye"></div>
      <div class="v-title" id="vTitle"></div>
      <div class="v-text" id="vText"></div>
      <div class="v-score" id="vScore"></div>
    </div>

    <div class="pills" id="pills"></div>

    <div class="gauge-card">
      <div class="g-lbl">TERMÔMETRO DE ATRATIVIDADE</div>
      <div class="g-track">
        <div class="g-fill" id="gFill" style="width:0%"></div>
        <div class="g-pin" id="gPin" style="left:0%"></div>
      </div>
      <div class="g-labs"><span>EVITAR</span><span>NEUTRO</span><span>ATRATIVO</span></div>
    </div>

    <!-- Contexto Setorial -->
    <div id="contextoSetorCard" style="display:none"></div>

    <!-- Alerta Político -->
    <div class="alerta-politico" id="alertaPolitico">
      <div class="ap-icon">⚠️</div>
      <div class="ap-body">
        <div class="ap-title">ALERTAS</div>
        <div class="ap-items" id="alertaPoliticoItems"></div>
      </div>
    </div>

    <!-- Score Final — logo abaixo do termômetro -->
    <div class="score-final-card" id="scoreFinalCard" style="display:none">
      <div>
        <div class="sf-label">SCORE FINAL</div>
        <div class="sf-score" id="sfScore" style="color:var(--gold2)">—</div>
        <div class="sf-sub">QUANT + QUALITATIVO</div>
      </div>
      <div class="sf-bars">
        <div class="sf-bar-row">
          <div class="sf-bar-label">QUANTITATIVO <span class="sf-tip" title="Baseado em dados numéricos: P/L, P/VP, ROE, DY, Liquidez, Endividamento. Representa 60% do Score Final.">ⓘ</span></div>
          <div class="sf-bar-track"><div class="sf-bar-fill" id="sfBarQuant" style="width:0%;background:var(--blue2)"></div></div>
          <div class="sf-bar-val" id="sfValQuant">—</div>
        </div>
        <div class="sf-bar-row">
          <div class="sf-bar-label">QUALITATIVO <span class="sf-tip" title="Análise de negócio: Moat, Previsibilidade de Receita, Gestão, Posição no Setor, Risco Regulatório. Representa 40% do Score Final.">ⓘ</span></div>
          <div class="sf-bar-track"><div class="sf-bar-fill" id="sfBarQual" style="width:0%;background:var(--gold2)"></div></div>
          <div class="sf-bar-val" id="sfValQual">—</div>
        </div>
      </div>
    </div>

    <div class="preco-card" id="precoCard"></div>

    <div class="analise-card" id="analiseCard">
      <div class="analise-hdr">ANÁLISE FUNDAMENTALISTA</div>
      <div class="analise-body" id="analiseBody"></div>
    </div>

    <div class="crit-card">
      <div class="crit-hdr">CRITÉRIOS ANALISADOS</div>
      <div id="critList"></div>
    </div>

    <!-- Análise Qualitativa -->
    <div class="qual-card" id="qualCard">
      <div class="qual-hdr">
        <div class="qual-hdr-left">ANÁLISE QUALITATIVA · IA</div>
        <div class="qual-score-badge" id="qualScoreBadge" style="display:none">—</div>
      </div>
      <div id="qualBody">
        <div class="qual-loading">
          <div class="qual-spinner"></div>
          Consultando inteligência artificial...
        </div>
      </div>
    </div>





    <div class="disc">
      ⚠️ Ferramenta educacional — não constitui recomendação de investimento.<br>
      Dados coletados automaticamente de fontes públicas. Verifique sempre antes de investir.<br>
      <strong>QuantTech Valor Justo</strong> · Análise fundamentalista para o investidor brasileiro
    </div>

  <!-- ── SCREENER ── sempre visível -->
  <div class="scr-card" style="margin-top:32px">
    <div class="scr-label">📊 SCREENER · RANKING — ANÁLISE EM LOTE</div>
    <div style="font-size:12px;color:rgba(255,255,255,.5);margin-bottom:14px">
      Digite vários tickers e receba um ranking ordenado por Score Final
    </div>
    <textarea class="scr-textarea" id="scrInput"
      placeholder="Ex: PETR4, VALE3, ITUB4, WEGE3, BBAS3, SAPR4, KEPL3, EGIE3"></textarea>
    <div class="scr-row">
      <button class="btn-screener" onclick="rodarScreener()" id="btnScr">
        📊 Gerar Ranking →
      </button>
      <div class="scr-progress" id="scrProg"></div>
    </div>
  </div>
  <div id="scrResultado"></div>

  </div>


<script>
const $=id=>document.getElementById(id);
const fmt=(n,d=2)=>isNaN(n)||n===null?'—':Number(n).toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d});

async function analisar(){
  const ticker=$('inp').value.trim().toUpperCase();
  if(!ticker){showErr('Digite o ticker. Ex: PETR4');return;}
  hideErr();
  $('dadosCard').classList.remove('on');
  $('result').style.display='none';
  $('loadTicker').textContent=ticker;
  $('load').classList.add('on');
  $('btn').disabled=true;
  try{
    const res=await fetch('/analisar?ticker='+encodeURIComponent(ticker));
    const d=await res.json();
    $('load').classList.remove('on');
    if(d.erro){showErr(d.erro);return;}
    render(d);
  }catch(e){
    $('load').classList.remove('on');
    showErr('Não foi possível conectar. Certifique-se que quanttech.py está rodando.');
  }
  $('btn').disabled=false;
}

function showErr(m){const e=$('err');e.textContent=m;e.classList.add('on');}
function hideErr(){$('err').classList.remove('on');}

function render(d){
  const dd=d.dados;

  // Dados card
  $('dTicker').textContent=d.ticker;
  $('dEmpresa').textContent=d.empresa+(d.setor&&d.setor!=='—'?' · '+d.setor:'');
  $('dGrid').innerHTML=[
    {l:'PREÇO',       v:'R$ '+fmt(dd.preco),                                    c:''},
    {l:'P/L',         v:fmt(dd.pl,1)+'x',     c:dd.pl>0&&dd.pl<15?'pos':dd.pl>25?'neg':''},
    {l:'P/VP',        v:fmt(dd.pvp,2)+'x',    c:dd.pvp<1.5?'pos':dd.pvp>2.5?'neg':''},
    {l:'ROE',         v:fmt(dd.roe,1)+'%',    c:dd.roe>=15?'pos':dd.roe<8?'neg':''},
    {l:'DY',          v:fmt(dd.dy,1)+'%',     c:dd.dy>=4?'pos':dd.dy<2?'neg':''},
    {l:'LPA',         v:'R$ '+fmt(dd.lpa),                                      c:''},
    {l:'VPA',         v:'R$ '+fmt(dd.vpa),                                      c:''},
    {l:'VAR. MÊS',    v:(dd.var_mes>=0?'+':'')+fmt(dd.var_mes,1)+'%',           c:dd.var_mes>=0?'pos':'neg'},
    {l:'IPCA 12M',    v:fmt(dd.ipca_12m,2)+'%',                                 c:'gld'},
    {l:'DÓLAR',        v:dd.dolar>0?'R$ '+fmt(dd.dolar,2):'—',                  c:dd.dolar>5.5?'neg':dd.dolar>5.0?'gld':'pos'},
  ].map(c=>`<div class="dado"><div class="d-lbl">${c.l}</div><div class="d-val ${c.c}">${c.v}</div></div>`).join('');
  $('dadosCard').classList.add('on');

  // Verdict
  const sc=d.score, pj=d.precos_justos, mg=pj.margem||0;
  const verd=sc>=65?'ATRATIVO':sc>=40?'NEUTRO':'CARO';
  const cls=verd==='ATRATIVO'?'buy':verd==='NEUTRO'?'hold':'avoid';
  $('verdict').className='verdict '+cls;
  $('vEye').textContent=verd==='ATRATIVO'?'✦ SINAL POSITIVO':verd==='NEUTRO'?'◈ SINAL NEUTRO':'⚠ SINAL DE CAUTELA';
  $('vTitle').textContent=verd==='ATRATIVO'?d.ticker+' parece atrativo':verd==='NEUTRO'?d.ticker+' exige atenção':d.ticker+' não parece barato agora';
  $('vText').textContent=verd==='ATRATIVO'
    ?'Os indicadores fundamentalistas apontam para um preço com desconto em relação ao valor intrínseco calculado. A combinação de múltiplos, rentabilidade e margem de segurança sugere atratividade para o investidor de longo prazo.'
    :verd==='NEUTRO'
    ?'A ação apresenta pontos positivos e negativos equilibrados. O preço está próximo do valor justo estimado, sem grande desconto nem prêmio excessivo. Vale monitorar e aguardar melhor ponto de entrada.'
    :'Os critérios indicam que o preço atual está elevado em relação aos fundamentos ou que a empresa apresenta fragilidades operacionais. Não significa má empresa — apenas que o momento pode não ser o ideal para entrada.';
  $('vScore').textContent=sc+'%';

  // Pills
  $('pills').innerHTML=[
    {l:'PONTUAÇÃO', v:sc+'%',            s:'de 100%',       c:sc>=65?'pos':sc>=40?'gld':'neg'},
    {l:'P/L',       v:fmt(dd.pl,1)+'x', s:'Preço/Lucro',   c:dd.pl>0&&dd.pl<15?'pos':dd.pl>25?'neg':''},
    {l:'P/VP',      v:fmt(dd.pvp,2)+'x',s:'Preço/Patrim.', c:dd.pvp<1.5?'pos':dd.pvp>2.5?'neg':''},
    {l:'DY',        v:fmt(dd.dy,1)+'%', s:'Dividend Yield', c:dd.dy>=4?'pos':dd.dy<2?'neg':''},
  ].map(p=>`<div class="pill"><div class="p-lbl">${p.l}</div><div class="p-val ${p.c}">${p.v}</div><div class="p-sub">${p.s}</div></div>`).join('');

  // Gauge
  setTimeout(()=>{$('gFill').style.width=sc+'%';$('gPin').style.left=sc+'%';},120);

  // ── Alerta Político ──
  const alertas = [];
  const setorLower = (d.setor||'').toLowerCase();
  const tickerUp = d.ticker||'';
  // Estatais conhecidas
  // Apenas empresas com controle estatal ATUAL (governo federal ou estadual majoritário)
  const estatais = {
    // Federal — controle direto da União
    'PETR4': 'Petrobras — União detém ~36% + golden share',
    'PETR3': 'Petrobras — União detém ~36% + golden share',
    'BBAS3': 'Banco do Brasil — União detém ~50%',
    // Estaduais — controle de governo estadual
    'SAPR4': 'Sanepar — Governo do Paraná majoritário',
    'SAPR3': 'Sanepar — Governo do Paraná majoritário',
    'SAPR11':'Sanepar — Governo do Paraná majoritário',
    'SBSP3': 'Sabesp — Estado de SP ainda majoritário (privatização parcial 2024)',
    'CSMG3': 'Copasa — Governo de Minas Gerais majoritário',
    'CMIG4': 'Cemig — Governo de Minas Gerais majoritário',
    'CMIG3': 'Cemig — Governo de Minas Gerais majoritário',
    'BRSR6': 'Banrisul — Governo do RS majoritário',
    'CESP6': 'CESP — Governo de SP com participação relevante',
    // Privatizadas recentemente — golden share ou participação residual
    'ELET3': 'Eletrobras — privatizada 2022, União mantém golden share',
    'ELET6': 'Eletrobras — privatizada 2022, União mantém golden share',
    'CPLE6': 'Copel — privatizada 2023, Estado do PR mantém golden share',
    'CPLE3': 'Copel — privatizada 2023, Estado do PR mantém golden share',
  };
  // VALE3, CSNA3, GGBR4 etc — privadas, sem controle estatal
  if(estatais[tickerUp]) alertas.push('EMPRESA ESTATAL - ' + estatais[tickerUp]);
  if(setorLower.includes('petro')||setorLower.includes('petró')) alertas.push('Setor de Petróleo - Interferência Governamental');
  if(setorLower.includes('saneam')) alertas.push('Saneamento - Dependência de Tarifas Reguladas');
  if(setorLower.includes('minera')) alertas.push('Mineração - Risco de Royalties e Regulação Ambiental');
  if(dd.div_patrim > 2.5) alertas.push('Endividamento muito elevado - Risco de Reestruturação');

  const apEl = $('alertaPolitico');
  if(alertas.length > 0){
    $('alertaPoliticoItems').innerHTML = alertas.map(a=>`- ${a}`).join('<br>');
    apEl.classList.add('on');
  } else {
    apEl.classList.remove('on');
  }

  // Preço Justo
  $('precoCard').innerHTML='<div class="pc-lbl">ESTIMATIVA DE PREÇO JUSTO</div>'
    +'<div class="pc-grid">'
    +(pj.graham?`<div><div class="pc-il">GRAHAM</div><div class="pc-iv">R$ ${fmt(pj.graham)}</div><div class="pc-is">√(22.5 × LPA × VPA)</div></div>`:'')
    +(pj.pl_justo?`<div><div class="pc-il">P/L JUSTO</div><div class="pc-iv">R$ ${fmt(pj.pl_justo)}</div><div class="pc-is">LPA × (8.5 + 2g)</div></div>`:'')
    +(pj.bazin?`<div><div class="pc-il">BAZIN</div><div class="pc-iv">R$ ${fmt(pj.bazin)}</div><div class="pc-is">Dividendo ÷ 6%</div></div>`:'')
    +(pj.roe_ke?`<div><div class="pc-il">ROE/Ke</div><div class="pc-iv">R$ ${fmt(pj.roe_ke)}</div><div class="pc-is">P/VP Justo × VPA</div></div>`:'')
    +'</div>'
    +(pj.media?`<div class="pc-bottom">
      <div>
        <div style="font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.4);letter-spacing:2px;margin-bottom:5px">PREÇO ALVO</div>
        <div style="font-family:'DM Serif Display',serif;font-size:34px;color:var(--gold2)">R$ ${fmt(pj.media)}</div>
      </div>
      <div style="text-align:right">
        <div style="font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.4);letter-spacing:2px;margin-bottom:5px">PREÇO ATUAL</div>
        <div style="font-family:'DM Serif Display',serif;font-size:34px;color:#fff">R$ ${fmt(dd.preco)}</div>
        <div style="font-size:12px;font-family:'DM Mono',monospace;margin-top:4px;color:${mg>=0?'#22c55e':'#ef4444'}">
          ${mg>=0?'▲ desconto de':'▼ prêmio de'} ${fmt(Math.abs(mg),1)}%
        </div>
      </div>
    </div>`:'');

  // Análise textual gerada localmente
  const analise=d.analise;
  $('analiseBody').innerHTML=[
    {l:'EMPRESA E SETOR',        t:analise.empresa},
    {l:'AVALIAÇÃO DE PREÇO',     t:analise.preco},
    {l:'PONTOS DE ATENÇÃO',      t:analise.atencao},
    {l:'PERSPECTIVA',            t:analise.perspectiva},
  ].filter(s=>s.t).map(s=>`
    <div class="analise-section">
      <div class="a-label">${s.l}</div>
      <div class="a-text">${s.t}</div>
    </div>
  `).join('');

  // Critérios
  const ic={pass:'✓',fail:'✗',warn:'!'};
  $('critList').innerHTML=d.criterios.map(c=>`
    <div class="crit">
      <div class="c-ic ${c.status}">${ic[c.status]}</div>
      <div class="c-body"><div class="c-nome">${c.nome}</div><div class="c-det">${c.detalhe}</div></div>
      <div class="c-badge ${c.status}">${c.badge}</div>
    </div>
  `).join('');

  // Contexto Setorial
  renderContextoSetor(d.contexto_setor, d.dados.dolar);

  // Qualitativa
  renderQualitativa(d.qualitativa, sc);

  $('result').style.display='block';
  $('result').scrollIntoView({behavior:'smooth',block:'start'});
}

function renderContextoSetor(ctx, dolar) {
  const el = document.getElementById('contextoSetorCard');
  if (!ctx) { el.style.display='none'; return; }
  const cor = ctx.cor || 'amarelo';
  el.style.display = 'block';

  // Bloco dólar
  let dolarHtml = '';
  if (dolar && dolar > 0 && ctx.dolar_tipo) {
    const dolarCor = ctx.dolar_tipo === 'positivo' ? '#16a34a' : ctx.dolar_tipo === 'negativo' ? '#dc2626' : '#92400e';
    const dolarEmoji = ctx.dolar_tipo === 'positivo' ? '💚' : ctx.dolar_tipo === 'negativo' ? '🔴' : '🟡';
    const dolarLabel = ctx.dolar_tipo === 'positivo' ? 'FAVORÁVEL' : ctx.dolar_tipo === 'negativo' ? 'PRESSÃO' : 'NEUTRO';
    dolarHtml = `
      <div class="cs-dolar" style="border-top:1px solid rgba(0,0,0,.08);margin-top:10px;padding-top:10px;
        display:flex;align-items:flex-start;gap:10px">
        <span style="font-size:16px">💵</span>
        <div>
          <span style="font-family:'DM Mono',monospace;font-size:10px;letter-spacing:1px;
            font-weight:700;color:${dolarCor}">${dolarEmoji} DÓLAR R$${dolar.toFixed(2).replace('.',',')} · ${dolarLabel}</span>
          <div style="font-size:11px;color:inherit;margin-top:2px;font-weight:300;opacity:.8">${ctx.dolar_texto}</div>
        </div>
      </div>`;
  }

  el.innerHTML = `
    <div class="contexto-setor ${cor}">
      <div class="cs-header">
        <div class="cs-titulo">${ctx.emoji} CONTEXTO SETORIAL · ${ctx.nome.toUpperCase()}</div>
        <div class="cs-badge">${ctx.status}</div>
      </div>
      <div class="cs-texto">${ctx.texto}</div>
      ${dolarHtml}
    </div>`;
}

function renderQualitativa(q, scoreQuant) {
  if (!q) {
    document.getElementById('qualBody').innerHTML =
      '<div class="qual-loading" style="color:var(--ink3)">Análise qualitativa indisponível no momento.</div>';
    return;
  }
  const scoreQual = q.score_qualitativo || 0;
  const scoreFinal = Math.round(scoreQuant * 0.6 + scoreQual * 0.4);

  // Score badge
  const badge = document.getElementById('qualScoreBadge');
  badge.textContent = scoreQual + '/100';
  badge.style.display = 'block';
  badge.style.background = scoreQual >= 65 ? 'var(--green)' : scoreQual >= 40 ? 'var(--gold)' : 'var(--red2)';

  // Score final
  document.getElementById('scoreFinalCard').style.display = 'flex';
  document.getElementById('sfScore').textContent = scoreFinal + '%';
  document.getElementById('sfScore').style.color = scoreFinal >= 65 ? 'var(--green2)' : scoreFinal >= 40 ? 'var(--gold2)' : 'var(--red2)';
  setTimeout(() => {
    document.getElementById('sfBarQuant').style.width = scoreQuant + '%';
    document.getElementById('sfValQuant').textContent = scoreQuant + '%';
    document.getElementById('sfBarQual').style.width = scoreQual + '%';
    document.getElementById('sfValQual').textContent = scoreQual + '%';
  }, 200);

  // Critérios
  const nivelClass = n => n === 'FORTE' ? 'forte' : n === 'FRACO' ? 'fraco' : 'medio';
  const nivelLabel = n => n === 'FORTE' ? 'FORTE' : n === 'FRACO' ? 'FRACO' : 'MÉDIO';
  const criteriosHtml = (q.criterios || []).map(c => {
    const nc = nivelClass(c.nivel);
    const pct = Math.round((c.nota / 20) * 100);
    return `<div class="qc">
      <div class="qc-bar-wrap">
        <div class="qc-bar-bg"><div class="qc-bar-fill ${nc}" style="width:${pct}%"></div></div>
        <div class="qc-nota">${c.nota}/20</div>
      </div>
      <div class="qc-body">
        <div class="qc-nome">${c.nome}</div>
        <div class="qc-just">${c.justificativa}</div>
      </div>
      <div class="qc-nivel ${nc}">${nivelLabel(c.nivel)}</div>
    </div>`;
  }).join('');

  document.getElementById('qualBody').innerHTML =
    '<div class="qual-criterios">' + criteriosHtml + '</div>' +
    (q.resumo ? `<div class="qual-resumo">${q.resumo}</div>` : '');
}

$('inp').addEventListener('input',e=>{e.target.value=e.target.value.toUpperCase();});
$('inp').addEventListener('keydown',e=>{if(e.key==='Enter')analisar();});

// ── TABS ──
function switchTab(tab){
  // Esconder todas as tabs
  ['tabAnalise','tabScreener'].forEach(id=>{
    const el=document.getElementById(id);
    if(el) el.style.display='none';
  });
  // Remover active dos botões
  document.querySelectorAll('.tab-nav-btn').forEach(b=>b.classList.remove('active'));
  // Mostrar a tab selecionada
  const show=tab==='analise'?'tabAnalise':'tabScreener';
  const el=document.getElementById(show);
  if(el) el.style.display='block';
  // Ativar botão
  const btnId=tab==='analise'?'tabBtnAnalise':'tabBtnScreener';
  const btn=document.getElementById(btnId);
  if(btn) btn.classList.add('active');
  // Scroll para as tabs
  document.querySelector('.tabs-nav').scrollIntoView({behavior:'smooth',block:'start'});
}

// ── SCREENER ──
async function rodarScreener(){
  const raw = $('scrInput').value;
  const tickers = raw.toUpperCase().split(/[,;\s]+/).map(t=>t.trim()).filter(t=>/^[A-Z]{4}[0-9]{1,2}$/.test(t));
  if(!tickers.length){
    $('scrResultado').innerHTML='<div style="color:var(--red2);font-family:monospace;font-size:12px;padding:12px">Nenhum ticker válido encontrado. Use formato: PETR4, VALE3...</div>';
    return;
  }
  const btn=$('btnScr'); btn.disabled=true; btn.textContent='⏳ Analisando...';
  $('scrResultado').innerHTML='';
  const resultados=[];
  for(let i=0;i<tickers.length;i++){
    const tk=tickers[i];
    $('scrProg').textContent=`Analisando ${tk}... (${i+1}/${tickers.length})`;
    try{
      const r=await fetch('/analisar?ticker='+tk);
      const d=await r.json();
      if(d.erro) resultados.push({ticker:tk,erro:d.erro});
      else resultados.push({ticker:tk,...d});
    }catch(e){resultados.push({ticker:tk,erro:'Falha de conexão'});}
    // Pequena pausa para não sobrecarregar
    await new Promise(res=>setTimeout(res,400));
  }
  $('scrProg').textContent=`✓ ${tickers.length} ações analisadas`;
  btn.disabled=false; btn.textContent='📊 Gerar Ranking →';
  renderRanking(resultados);
}

function renderRanking(resultados){
  // Separar erros dos válidos
  const validos=resultados.filter(r=>!r.erro);
  const erros=resultados.filter(r=>r.erro);

  // Ordenar por score_final desc
  validos.sort((a,b)=>(b.score_final||0)-(a.score_final||0));

  let html='<div class="ranking-card">';
  html+=`<div class="ranking-hdr">
    <span class="rh-title">RANKING · SCORE FINAL</span>
    <span class="rh-count">${validos.length} ações ordenadas</span>
  </div>`;

  if(!validos.length){
    html+='<div style="padding:20px;color:var(--ink4);font-size:13px">Nenhuma ação analisada com sucesso.</div>';
  }

  validos.forEach((r,i)=>{
    const pos=i+1;
    const numClass=pos===1?'gold':pos===2?'silver':pos===3?'bronze':'';
    const d=r.dados||{};
    const sf=r.score_final||0;
    const scoreClass=sf>=70?'alto':sf>=50?'medio':'baixo';
    const preco=d.preco||0;
    const alvo=r.preco_alvo||0;
    const desc=alvo>0&&preco>0?((alvo-preco)/preco*100):0;
    const descClass=desc>0?'pos':'neg';
    const descTxt=desc!==0?(desc>0?'▲ +':'▼ ')+Math.abs(desc).toFixed(1)+'%':'—';
    const sinalEmoji=r.sinal==='compra'?'✦':r.sinal==='neutro'?'◆':'✕';
    const sinalColor=r.sinal==='compra'?'var(--green)':r.sinal==='neutro'?'var(--gold)':'var(--red2)';
    const setor=r.setor_detectado||d.setor||'—';
    const ctx=r.contexto_setor;
    const ctxEmoji=ctx?ctx.emoji:'🏢';
    const ctxCor=ctx?ctx.cor:'cinza';
    const ctxCorVar=ctxCor==='verde'?'var(--green)':ctxCor==='vermelho'?'var(--red2)':'var(--gold)';

    // Impacto do dólar
    const dolarTipo = ctx?ctx.dolar_tipo:null;
    const dolarVal  = d.dolar||0;
    let dolarBadge  = '';
    if(dolarTipo && dolarVal>0){
      const dEmoji = dolarTipo==='positivo'?'💚':dolarTipo==='negativo'?'🔴':'⚪';
      const dTxt   = dolarTipo==='positivo'?'USD FAVORECE':dolarTipo==='negativo'?'USD PRESSIONA':'USD NEUTRO';
      const dColor = dolarTipo==='positivo'?'#22c55e':dolarTipo==='negativo'?'#ef4444':'#94a3b8';
      dolarBadge   = `<span style="font-size:9px;font-family:'DM Mono',monospace;letter-spacing:.5px;
        color:${dColor};border:1px solid ${dColor};padding:1px 6px;border-radius:8px;
        white-space:nowrap;opacity:.85">${dEmoji} ${dTxt}</span>`;
    }

    html+=`<div class="rk-item" onclick="irParaAnalise('${r.ticker}')">
      <div class="rk-num ${numClass}">${pos}</div>
      <div class="rk-body">
        <div class="rk-top">
          <span class="rk-ticker">${r.ticker}</span>
          <span class="rk-empresa">${d.empresa||r.ticker}</span>
          <span class="rk-setor">${setor}</span>
          <span class="rk-ctx" title="${ctx?ctx.nome:''}">${ctxEmoji}</span>
        </div>
        <div class="rk-bottom">
          <span class="rk-preco">R$ ${preco.toFixed(2).replace('.',',')}</span>
          <span class="rk-alvo">→ Alvo R$ ${alvo>0?alvo.toFixed(2).replace('.',','):'—'}</span>
          <span class="rk-desc ${descClass}">${descTxt}</span>
          <span style="font-size:11px;color:${sinalColor};font-weight:700">${sinalEmoji} ${(r.sinal||'—').toUpperCase()}</span>
          ${dolarBadge}
        </div>
      </div>
      <div class="rk-right">
        <div class="rk-sinal" style="color:${ctxCorVar}">${ctxEmoji}</div>
        <div class="rk-score ${scoreClass}">${sf.toFixed(0)}%</div>
        <div class="rk-scorelbl">SCORE</div>
      </div>
    </div>`;
  });

  // Erros no final
  erros.forEach(r=>{
    html+=`<div class="rk-erro">⚠ ${r.ticker} — ${r.erro}</div>`;
  });

  html+='</div>';

  // Resumo estatístico
  if(validos.length>1){
    const compra=validos.filter(r=>r.sinal==='compra').length;
    const neutro=validos.filter(r=>r.sinal==='neutro').length;
    const evitar=validos.filter(r=>r.sinal==='evitar').length;
    const mediaScore=(validos.reduce((s,r)=>s+(r.score_final||0),0)/validos.length).toFixed(1);
    html+=`<div style="background:var(--paper);border:1px solid var(--border);border-radius:12px;
      padding:18px 22px;display:flex;gap:28px;flex-wrap:wrap;align-items:center">
      <div style="font-family:'DM Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--ink4)">RESUMO DO LOTE</div>
      <div style="font-size:13px">✦ <b style="color:var(--green)">${compra}</b> compra</div>
      <div style="font-size:13px">◆ <b style="color:var(--gold)">${neutro}</b> neutro</div>
      <div style="font-size:13px">✕ <b style="color:var(--red2)">${evitar}</b> evitar</div>
      <div style="font-size:13px">📊 Score médio: <b>${mediaScore}%</b></div>
    </div>`;
  }

  $('scrResultado').innerHTML=html;
}

function irParaAnalise(ticker){
  switchTab('analise');
  $('inp').value=ticker;
  analisar();
}

</script>
</body>
</html>"""

# ─── Coleta de dados ──────────────────────────────────────────────────────────
def fetch(url, timeout=12):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.fundamentus.com.br/",
    })
    import gzip
    resp = urlopen(req, timeout=timeout)
    raw = resp.read()
    # Descomprime gzip se necessário
    try:
        raw = gzip.decompress(raw)
    except:
        pass
    return raw.decode("utf-8", errors="ignore")

def fetch_json(url, timeout=8):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urlopen(req, timeout=timeout).read().decode())

def num(texto):
    """Converte string brasileira para float. Ex: '1.234,56' -> 1234.56"""
    if not texto: return 0.0
    t = re.sub(r'[^\d,.\-]', '', texto.strip())
    if ',' in t and '.' in t:
        t = t.replace('.', '').replace(',', '.')
    elif ',' in t:
        t = t.replace(',', '.')
    try: return float(t)
    except: return 0.0

def buscar_fundamentus(ticker):
    """Busca dados reais do Fundamentus com múltiplos padrões robustos"""
    html = fetch(f"https://www.fundamentus.com.br/detalhes.php?papel={ticker.upper()}")

    # Ticker inválido — página vazia ou sem resultados
    if len(html) < 1000 or "Nenhum papel encontrado" in html:
        return {"ticker": ticker.upper(), "preco": 0.0, "empresa": ticker.upper(), "_pagina_invalida": True}

    d = {"ticker": ticker.upper(), "_pagina_invalida": False}

    def strip(s):
        return re.sub(r'<[^>]+>', '', s).strip()

    # ── Nome da empresa ──
    for pat in [
        r'id="ctl00_cph1_lblNome"[^>]*>(.*?)</span>',
        r'lblNome[^>]*>(.*?)</span>',
        r'Empresa\s*</td>\s*<td[^>]*>(.*?)</td>',
    ]:
        m = re.search(pat, html, re.DOTALL | re.I)
        if m and strip(m.group(1)):
            d["empresa"] = strip(m.group(1)); break
    else:
        d["empresa"] = ticker.upper()

    # ── Setor ──
    for pat in [
        r'Subsetor\s*</td>\s*<td[^>]*>(.*?)</td>',
        r'Setor\s*</td>\s*<td[^>]*>(.*?)</td>',
    ]:
        m = re.search(pat, html, re.DOTALL | re.I)
        if m and strip(m.group(1)):
            d["setor"] = strip(m.group(1)); break
    else:
        d["setor"] = "—"

    # ── Extrator genérico: parse de TODOS os pares label->valor da tabela ──
    tabela_dados = {}
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.I)
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.I)
        i = 0
        while i < len(cells) - 1:
            label_cell = strip(cells[i]).replace(' ', ' ').strip()
            value_cell = strip(cells[i+1]).replace(' ', ' ').strip()
            if label_cell and value_cell and re.search(r'[\d]', value_cell):
                tabela_dados[label_cell] = value_cell
            i += 2

    def get_val(label):
        # Busca exata
        if label in tabela_dados:
            return tabela_dados[label]
        # Busca parcial normalizada
        label_norm = label.lower().replace('.', '').replace(' ', '')
        for k, v in tabela_dados.items():
            if label_norm in k.lower().replace('.', '').replace(' ', ''):
                return v
        return ""

    # ── Preço: busca robusta em cascata ──
    preco = 0.0

    # Estratégia 1: percorre tabela_dados e acha qualquer chave que contenha "cota"
    # Remove TODOS os chars não-alfanuméricos antes de comparar (fix do ?Cotao, Cotação, etc)
    for k, v in tabela_dados.items():
        k_clean = re.sub(r'[^a-zA-Z]', '', k.lower()
            .replace('ç', 'c').replace('ã', 'a').replace('à', 'a')
            .replace('á', 'a').replace('â', 'a').replace('ä', 'a')
            .replace('õ', 'o').replace('ó', 'o').replace('ô', 'o')
        )
        if k_clean.startswith('cota') or k_clean == 'cotacao':
            parsed = num(v)
            if parsed > 0:
                preco = parsed
                break

    # Estratégia 2: regex com IDs conhecidos
    if preco == 0:
        for pat in [
            r'id="ctl00_cph1_lblCotacao"[^>]*>([\d.,]+)',
            r'lblCotacao[^>]*>([\d.,]+)',
        ]:
            m = re.search(pat, html, re.DOTALL | re.I)
            if m:
                v = num(m.group(1))
                if v > 0:
                    preco = v
                    break

    # Estratégia 3: regex genérico — qualquer célula com "cota" seguida de número
    if preco == 0:
        m = re.search(r'Cota[^<]{0,20}</td>\s*<td[^>]*>\s*(?:<[^>]+>)*([\d.,]+)', html, re.DOTALL | re.I)
        if m:
            v = num(m.group(1))
            if v > 0:
                preco = v

    # Estratégia 4: primeiro número após "cota" no HTML
    if preco == 0:
        idx = html.lower().find('cota')
        if idx >= 0:
            ns = re.findall(r'>([\d]+[.,][\d]{2})<', html[idx:idx+800])
            for n in ns:
                v = num(n)
                if v > 0:
                    preco = v
                    break

    # ── Fallback: se preco ainda 0, busca via Yahoo Finance ──
    if preco == 0:
        chaves = list(tabela_dados.keys())
        print(f"  ⚠️  preco=0 via Fundamentus para {ticker}. Tentando Yahoo Finance...")
        print(f"  Chaves encontradas: {chaves[:15]}")
        try:
            yf_data = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA?interval=1d&range=1d")
            yf_preco = yf_data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            if yf_preco and yf_preco > 0:
                preco = round(float(yf_preco), 2)
                print(f"  ✅ Preço via Yahoo Finance: R${preco:.2f}")
        except Exception as e:
            print(f"  ❌ Yahoo Finance também falhou: {e}")

    d["preco"] = preco

    # ── Indicadores ──
    for label, campo in [
        ("P/L","pl"), ("P/VP","pvp"), ("P/EBIT","p_ebit"),
        ("Div. Yield","dy"), ("ROE","roe"), ("ROIC","roic"),
        ("LPA","lpa"), ("VPA","vpa"),
        ("Marg. Bruta","marg_bruta"), ("Marg. EBIT","marg_ebit"),
        ("Marg. Líquida","marg_liq"), ("Dív. Bruta/Patrim.","div_patrim"),
        ("Liquidez Corr","liq_corr"), ("Cresc. Rec. 5a","cresc_5a"),
        ("EV/EBITDA","ev_ebitda"), ("Giro Ativos","giro_ativos"),
        ("Dív. Líquida","div_liquida"),
    ]:
        d[campo] = num(get_val(label))

    # Dividendos estimados
    d["dividendo12m"] = round(d["preco"] * d["dy"] / 100, 2) if d.get("dy") and d.get("preco") else 0.0

    return d


def buscar_investidor10(ticker):
    """Busca dados complementares do Investidor10"""
    extra = {}
    try:
        html = fetch(f"https://investidor10.com.br/acoes/{ticker.lower()}/", timeout=10)

        # P/L
        m = re.search(r'P/L.*?<span[^>]*>([\d.,]+)</span>', html, re.DOTALL | re.I)
        if m: extra["pl_i10"] = num(m.group(1))

        # DY
        m = re.search(r'Dividend Yield.*?<span[^>]*>([\d.,]+)\s*%', html, re.DOTALL | re.I)
        if m: extra["dy_i10"] = num(m.group(1))

        # ROE
        m = re.search(r'\bROE\b.*?<span[^>]*>([\d.,]+)\s*%', html, re.DOTALL | re.I)
        if m: extra["roe_i10"] = num(m.group(1))

        # Payout
        m = re.search(r'Payout.*?<span[^>]*>([\d.,]+)\s*%', html, re.DOTALL | re.I)
        if m: extra["payout"] = num(m.group(1))

        # Crescimento de lucro
        m = re.search(r'Cresc.*?Lucro.*?<span[^>]*>([\d.,\-]+)\s*%', html, re.DOTALL | re.I)
        if m: extra["cresc_lucro"] = num(m.group(1))

    except:
        pass
    return extra


def buscar_dolar():
    """Cotação atual do dólar — múltiplos fallbacks"""
    # Fonte 1: AwesomeAPI
    try:
        data = fetch_json("https://economia.awesomeapi.com.br/json/last/USD-BRL")
        val = float(data["USDBRL"]["bid"])
        if val > 0: return round(val, 2)
    except: pass
    # Fonte 2: Yahoo Finance
    try:
        data = fetch_json("https://query1.finance.yahoo.com/v8/finance/chart/USDBRL=X?interval=1d&range=1d")
        val = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        if val > 0: return round(float(val), 2)
    except: pass
    # Fonte 3: BCB PTAX última disponível
    try:
        from datetime import datetime, timedelta
        for delta in range(0, 5):
            dt = (datetime.now() - timedelta(days=delta)).strftime("%m-%d-%Y")
            url = f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{dt}'&$top=1&$format=json&$select=cotacaoCompra"
            data = fetch_json(url, timeout=6)
            if data.get("value"):
                return round(float(data["value"][0]["cotacaoCompra"]), 2)
    except: pass
    # Fallback fixo razoável
    return 5.85

def buscar_ipca():
    """IPCA acumulado 12 meses - Banco Central"""
    try:
        data = fetch_json("https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/12?formato=json")
        total = 1.0
        for item in data:
            total *= (1 + float(item["valor"].replace(",", ".")) / 100)
        return round((total - 1) * 100, 2)
    except:
        return 4.83  # fallback

def buscar_var(symbol):
    """Variação mensal via Yahoo Finance"""
    try:
        data = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1mo&range=2mo")
        closes = [c for c in data["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
        if len(closes) >= 2:
            return round((closes[-1] / closes[-2] - 1) * 100, 2)
    except:
        pass
    return 0.0


# ─── Cálculo de Preço Justo ───────────────────────────────────────────────────
def calcular_preco_justo(d, cresc=5, tipo="geral"):
    lpa   = d.get("lpa", 0)
    vpa   = d.get("vpa", 0)
    div   = d.get("dividendo12m", 0)
    roe   = d.get("roe", 0)
    preco = d.get("preco", 0)
    r = {}

    # Graham: útil para valor/util/banco, distorce para crescimento
    if lpa > 0 and vpa > 0 and tipo not in ("cresc",):
        r["graham"] = round(math.sqrt(22.5 * lpa * vpa), 2)

    # P/L Justo: NÃO usado para crescimento (LPA baixo distorce resultado)
    if lpa > 0 and tipo not in ("cresc",):
        r["pl_justo"] = round(lpa * (8.5 + 2 * cresc), 2)

    # Bazin: faz sentido para dividendos/util, não para crescimento
    if div > 0 and tipo not in ("cresc",):
        r["bazin"] = round(div / 0.06, 2)

    # ── Método P/L com crescimento real (validado vs consenso de analistas) ──
    # Prioridade 1: cresc_5a real do Fundamentus (mais preciso)
    # Prioridade 2: ROE × retenção setorial (fallback quando cresc_5a = 0)
    # Referência: fórmula Graham modificada LPA × (8.5 + 2g), alinhada com sell-side
    if tipo == "cresc" and lpa > 0 and roe > 0:
        setor_str = (d.get("setor") or "").lower()
        cresc_real = d.get("cresc_5a", 0) or 0

        # Cap do g por ciclicidade do setor
        eh_ciclico_g = any(x in setor_str for x in ["agrícol","agricol","agríco","sider","celulose","petro","minera","cicl","commod"])
        cap_g = 7.0 if eh_ciclico_g else 20.0  # cíclicos: g máx 7%, crescimento: 20%

        if cresc_real >= 5:
            # Dado real disponível — usar diretamente com cap por ciclicidade
            g_final = min(cresc_real, cap_g)
        else:
            # Fallback: retenção setorial × ROE
            if any(x in setor_str for x in ["saúde","saude","hospital","medic","farm"]):
                retencao = 0.38
            elif any(x in setor_str for x in ["agrícol","agricol","agríco"]):
                retencao = 0.28  # cíclico, retenção baixa
            elif any(x in setor_str for x in ["tecnol","softw","inform"]):
                retencao = 0.60
            elif any(x in setor_str for x in ["varejo","comerci","consum"]):
                retencao = 0.33
            else:
                retencao = 0.48  # indústria/máquinas/geral
            g_final = max(8.0, min(roe * retencao, 20.0))

        # LPA: corrige subdimensionamento do Fundamentus via preço/P.L atual
        pl_atual = d.get("pl", 0) or 0
        lpa_via_pl = (preco / pl_atual) if pl_atual > 0 and preco > 0 else 0
        lpa_efetivo = max(lpa, lpa_via_pl * 0.90)

        # Fórmula de valuation adaptada ao perfil
        if eh_ciclico_g:
            # Cíclicos: usar P/L de referência setorial (não Graham modificado)
            # Graham superestima cíclicos porque g alto é temporário
            pl_ref_ciclico = 12.0  # P/L justo para máquinas agrícolas/cíclicos
            r["roe_ke"] = round(lpa_efetivo * pl_ref_ciclico, 2)
        else:
            # Crescimento secular: Graham modificado com g real
            r["roe_ke"] = round(lpa_efetivo * (8.5 + 2 * g_final), 2)

    if r:
        media = sum(r.values()) / len(r)
        # Cap de segurança: preço alvo não pode ser mais que 60% acima do preço atual
        # Upsides >60% geralmente indicam dado distorcido (LPA subdimensionado, cresc_5a inflado)
        if preco > 0:
            cap_upside = preco * 1.60
            if media > cap_upside:
                media = cap_upside
                r["alerta_cap"] = True  # flag para exibir aviso no frontend
        r["media"]  = round(media, 2)
        r["margem"] = round((media - preco) / media * 100, 1) if media > 0 else 0
    else:
        r["media"]  = 0
        r["margem"] = 0

    return r


# ─── Score e Critérios ────────────────────────────────────────────────────────
def calcular_score(d, pj, tipo="geral"):
    pts = 0; mx = 0; cr = []

    pl      = d.get("pl", 0)
    pvp     = d.get("pvp", 0)
    roe     = d.get("roe", 0)
    dy      = d.get("dy", 0)
    div     = d.get("dividendo12m", 0)
    var_a   = d.get("var_mes", 0)
    var_i   = d.get("var_ibov_mes", 0)
    ipca    = d.get("ipca_12m", 0)
    mg      = pj.get("margem", 0)
    liq     = d.get("liq_corr", 0)
    div_p   = d.get("div_patrim", 0)
    marg_l  = d.get("marg_liq", 0)

    plref  = {"banco":9,"util":14,"cicl":10,"cresc":35,"div":14,"valor":11,"geral":15}.get(tipo, 15)
    pvpref = {"banco":1.2,"util":1.5,"cicl":1.2,"cresc":6.0,"div":2.0,"valor":1.0,"geral":2.5}.get(tipo, 2.5)
    roeref = {"banco":12,"util":10,"cicl":12,"cresc":20,"div":12,"valor":10,"geral":12}.get(tipo, 12)
    dyref  = {"banco":4,"util":5,"cicl":3,"cresc":1,"div":6,"valor":3,"geral":4}.get(tipo, 4)

    def add(nome, status, badge, det, peso, ok_pts, warn_pts=0):
        nonlocal pts, mx
        cr.append({"nome": nome, "status": status, "badge": badge, "detalhe": det})
        pts += ok_pts if status == "pass" else (warn_pts if status == "warn" else 0)
        mx  += peso

    # ── Pesos por critério e perfil ──
    w_pl  = {"cresc":0.5, "div":1.5, "valor":2.0}.get(tipo, 1.0)
    w_pvp = {"cresc":0.3, "div":1.0, "valor":2.0, "banco":2.0}.get(tipo, 1.0)
    w_roe = {"cresc":2.5, "div":1.0, "valor":1.5, "banco":1.5}.get(tipo, 1.0)
    w_dy  = {"cresc":0.3, "div":2.5, "util":2.0}.get(tipo, 1.0)
    w_ms  = {"cresc":0.5, "div":1.5, "valor":2.5}.get(tipo, 1.0)

    # ── Mensagens contextuais por perfil ──
    def msg_pl(v):
        if tipo == "cresc": return f"P/L {v:.1f}x — empresa de crescimento; múltiplo elevado é esperado se ROE e lucro crescem"
        if tipo == "cicl":  return f"P/L {v:.1f}x — empresa cíclica; P/L pode estar distorcido pelo ciclo de commodities"
        return f"P/L {v:.1f}x — {'atrativo' if v < plref else 'elevado'} para o perfil (referência: {plref}x)"
    def msg_pvp(v):
        if tipo == "cresc": return f"P/VP {v:.2f}x — prêmio justificado por ROE alto e crescimento consistente"
        if tipo == "banco": return f"P/VP {v:.2f}x — múltiplo chave para bancos; abaixo de 1.2x é conservador"
        return f"P/VP {v:.2f}x — {'desconto sobre patrimônio' if v<1 else 'dentro do esperado' if v<pvpref else 'acima do patrimônio'}"
    def msg_roe(v):
        if tipo == "cresc": return f"ROE {v:.1f}% — {'excelente' if v>=20 else 'bom'}, critério principal para empresa de crescimento"
        if tipo == "banco": return f"ROE {v:.1f}% — {'acima da média bancária' if v>=15 else 'dentro do esperado para o setor'}"
        return f"ROE {v:.1f}% — {'alta rentabilidade, gera valor' if v>=roeref else 'rentabilidade moderada' if v>=8 else 'baixa rentabilidade'}"
    def msg_dy(v):
        if tipo == "cresc": return f"DY {v:.1f}% — empresa de crescimento reinveste lucro; DY baixo é esperado e aceitável"
        if tipo == "div":   return f"DY {v:.1f}% — {'excelente' if v>=dyref else 'abaixo do esperado para empresa focada em dividendos'}"
        return f"DY {v:.1f}% — {'boa remuneração' if v>=dyref else 'dividendo modesto' if v>=2 else 'abaixo da inflação'}"

    # 1. P/L — para crescimento usa PEG Ratio (P/L ÷ crescimento), muito mais justo
    cresc5 = d.get("cresc_5a", 0) or 0
    if tipo == "cresc" and cresc5 > 0 and pl > 0:
        peg = pl / cresc5
        plok = peg < 1.5;  plw = peg < 2.5
        pl_detalhe = f"P/L {pl:.1f}x · PEG {peg:.2f} — {'excelente: crescimento justifica o múltiplo' if plok else 'aceitável para empresa de alto crescimento' if plw else 'múltiplo elevado mesmo ajustado pelo crescimento'}"
        add("Preço / Lucro (P/L)",
            "pass" if plok else "warn" if plw else "fail",
            f"{pl:.1f}x (PEG {peg:.1f})",
            pl_detalhe,
            2*w_pl, 2*w_pl, 1*w_pl if plw else 0)
    else:
        plok = 0 < pl < plref; plw = 0 < pl < plref * 1.4
        add("Preço / Lucro (P/L)",
            "pass" if plok else "warn" if plw else "fail",
            f"{pl:.1f}x" if pl > 0 else "N/A",
            msg_pl(pl) if pl > 0 else "Empresa sem lucro no período",
            2*w_pl, 2*w_pl, 1*w_pl if plw else 0)

    # 2. P/VP — para crescimento: calcula P/VP justo via ROE/Ke
    if tipo == "cresc" and roe > 0 and pvp > 0:
        ke = 0.12  # custo de capital referência
        g_perp = min(cresc5 / 100 if cresc5 > 0 else 0.05, 0.08)
        pvp_justo = (roe / 100 - g_perp) / (ke - g_perp) if ke > g_perp else pvpref
        pvp_justo = max(1.5, min(pvp_justo, 10.0))
        pvpok = pvp < pvp_justo * 0.85; pvpw = pvp < pvp_justo * 1.15
        pvp_det = f"P/VP {pvp:.2f}x · P/VP justo pelo ROE: {pvp_justo:.1f}x — {'abaixo do justo, prêmio não capturado' if pvpok else 'próximo do valor justo pelo ROE' if pvpw else 'acima do P/VP justo pelo ROE'}"
        add("Preço / Patrimônio (P/VP)",
            "pass" if pvpok else "warn" if pvpw else "fail",
            f"{pvp:.2f}x (justo {pvp_justo:.1f}x)",
            pvp_det,
            1.5*w_pvp, 1.5*w_pvp, 0.7*w_pvp if pvpw else 0)
    else:
        pvpok = pvp < pvpref * 0.7; pvpw = pvp < pvpref
        add("Preço / Patrimônio (P/VP)",
            "pass" if pvpok else "warn" if pvpw else "fail",
            f"{pvp:.2f}x",
            msg_pvp(pvp),
            1.5*w_pvp, 1.5*w_pvp, 0.7*w_pvp if pvpw else 0)

    # 3. ROE — peso aumentado para crescimento
    roeok = roe >= roeref; roew = roe >= roeref * 0.6
    add("Retorno sobre Patrimônio (ROE)",
        "pass" if roeok else "warn" if roew else "fail",
        f"{roe:.1f}%",
        msg_roe(roe),
        2*w_roe, 2*w_roe, 0.8*w_roe if roew else 0)

    # 4. DY — peso reduzido para crescimento, aumentado para dividendos
    dyok = dy >= dyref; dyw = dy >= dyref * 0.5
    add("Dividend Yield",
        "pass" if dyok else "warn" if dyw else "fail",
        f"{dy:.1f}%" if div > 0 else "—",
        msg_dy(dy),
        1*w_dy, 1*w_dy, 0.4*w_dy if dyw else 0)

    # 5. Margem de Segurança — peso menor para crescimento (Graham subestima)
    msok = mg >= 25; msw = mg >= 0
    if tipo == "cresc":
        ms_det = f"Preço {abs(mg):.1f}% {'abaixo' if mg>0 else 'acima'} do valor justo — para crescimento, Graham pode subestimar o valor real"
    else:
        ms_det = f"Preço {mg:.1f}% {'abaixo do valor justo — boa margem de segurança' if mg>0 else 'acima do valor justo — risco de sobrevalorização'}"
    add("Margem de Segurança",
        "pass" if msok else "warn" if msw else "fail",
        f"+{mg:.1f}%" if mg > 0 else f"{mg:.1f}%",
        ms_det,
        2*w_ms, 2*w_ms, 0.5*w_ms if msw else 0)

    # 6. Liquidez Corrente
    liqok = liq >= 1.5; liqw = liq >= 1.0
    add("Liquidez Corrente",
        "pass" if liqok else "warn" if liqw else "fail",
        f"{liq:.2f}x",
        f"Liquidez {liq:.2f}x — {'empresa saudável financeiramente no curto prazo' if liqok else 'liquidez aceitável mas apertada' if liqw else 'liquidez baixa — risco de dificuldade financeira'}",
        1, 1, 0.4 if liqw else 0)

    # 7. Endividamento — 0.00 significa dado não capturado, tratar como neutro
    if div_p == 0:
        add("Endividamento (Dív/Patrim.)",
            "warn", "N/D",
            "Dados de endividamento não disponíveis. Verifique o balanço diretamente.",
            1, 0, 0.5)
    else:
        endok = div_p < 0.5; endw = div_p < 1.5
        add("Endividamento (Dív/Patrim.)",
            "pass" if endok else "warn" if endw else "fail",
            f"{div_p:.2f}x",
            f"Dívida/Patrimônio {div_p:.2f}x — {'endividamento controlado' if endok else 'endividamento moderado' if endw else 'endividamento elevado — risco relevante'}",
            1, 1, 0.5 if endw else 0)

    # 8. vs IBOV — só pontua se tiver dado real de variação
    if var_a == 0 and var_i == 0:
        add("Performance vs IBOV", "warn", "N/D",
            "Variação mensal indisponível no momento. Consulte cotações em tempo real.",
            0.5, 0, 0.25)
    else:
        ibovok = var_a > var_i; ibovw = abs(var_a - var_i) < 1
        add("Performance vs IBOV",
            "pass" if ibovok else "warn" if ibovw else "fail",
            f"{'+' if var_a >= 0 else ''}{var_a:.1f}% vs {'+' if var_i >= 0 else ''}{var_i:.1f}%",
            f"{'Superou o Ibovespa em' if ibovok else 'Ficou próximo,' if ibovw else 'Ficou abaixo,'} {abs(var_a-var_i):.1f} p.p. no mês",
            0.5, 0.5, 0.2 if ibovw else 0)

    # 9. vs IPCA — só pontua se tiver dado real
    if var_a == 0:
        add("Performance vs IPCA", "warn", "N/D",
            "Variação mensal indisponível. Dado necessário para comparação com inflação.",
            0.5, 0, 0.25)
    else:
        ipcaok = var_a > ipca / 12
        add("Performance vs IPCA",
            "pass" if ipcaok else "fail",
            f"Ação {var_a:.1f}% / IPCA {ipca/12:.2f}%/mês",
            f"{'Preservou poder de compra no período' if ipcaok else 'Rendeu abaixo da inflação no mês'}",
            0.5, 0.5)

    score = round(pts / mx * 100) if mx > 0 else 0
    return score, cr


# ─── Análise textual local (sem IA externa) ───────────────────────────────────
def gerar_analise(d, pj, score, tipo):
    ticker  = d.get("ticker", "")
    empresa = d.get("empresa", ticker)
    setor   = d.get("setor", "—")
    if not setor or setor == "—":
        setor = TICKER_SETOR_MAP.get(ticker, "—")
    preco   = d.get("preco", 0)
    pl      = d.get("pl", 0)
    pvp     = d.get("pvp", 0)
    roe     = d.get("roe", 0)
    dy      = d.get("dy", 0)
    marg_l  = d.get("marg_liq", 0)
    div_p   = d.get("div_patrim", 0)
    cresc5  = d.get("cresc_5a", 0)
    media   = pj.get("media", 0)
    mg      = pj.get("margem", 0)

    # Empresa e setor
    txt_empresa = f"{empresa} ({ticker}) atua no setor de {setor}. "
    if roe >= 15:
        txt_empresa += f"A empresa demonstra alta rentabilidade com ROE de {roe:.1f}%, indicando boa geração de valor sobre o capital dos acionistas."
    elif roe >= 8:
        txt_empresa += f"Apresenta rentabilidade moderada com ROE de {roe:.1f}%."
    else:
        txt_empresa += f"O ROE de {roe:.1f}% indica dificuldade em rentabilizar o capital próprio — ponto de atenção relevante."

    # Avaliação de preço
    if media > 0:
        if mg >= 25:
            txt_preco = f"Com preço atual de R$ {preco:.2f} e valor justo médio estimado em R$ {media:.2f}, a ação negocia com desconto de {mg:.1f}%. "
            txt_preco += f"O P/L de {pl:.1f}x e P/VP de {pvp:.2f}x reforçam a atratividade dos múltiplos no momento."
        elif mg >= 0:
            txt_preco = f"O preço de R$ {preco:.2f} está próximo do valor justo estimado de R$ {media:.2f} (desconto de apenas {mg:.1f}%). "
            txt_preco += "A margem de segurança é baixa — o ativo está próximo do seu preço justo."
        else:
            txt_preco = f"Com preço atual de R$ {preco:.2f} acima do valor justo estimado de R$ {media:.2f} ({abs(mg):.1f}% de prêmio), "
            txt_preco += "o investidor estaria pagando acima do valor intrínseco calculado pelos modelos quantitativos."
    else:
        txt_preco = f"Preço atual: R$ {preco:.2f}. Dados insuficientes para calcular valor justo pelos modelos."

    # Pontos de atenção
    alertas = []
    if div_p > 1.0: alertas.append(f"endividamento elevado ({div_p:.2f}x patrimônio)")
    if marg_l < 5 and marg_l > 0: alertas.append(f"margem líquida apertada ({marg_l:.1f}%)")
    if cresc5 < 0: alertas.append(f"receita em queda nos últimos 5 anos ({cresc5:.1f}%)")
    if dy < 2 and dy > 0: alertas.append(f"dividend yield baixo ({dy:.1f}%)")
    if pl > 20: alertas.append(f"P/L elevado ({pl:.1f}x)")

    if alertas:
        txt_atencao = "Pontos que merecem monitoramento: " + "; ".join(alertas) + ". Recomenda-se verificar os balanços mais recentes antes de tomar qualquer decisão."
    else:
        txt_atencao = "Os indicadores quantitativos não apontam alertas críticos. A empresa apresenta fundamentos equilibrados nos critérios analisados."

    # Perspectiva
    if score >= 65:
        txt_persp = f"Com pontuação de {score}% nos critérios fundamentalistas, o ativo apresenta características favoráveis para o investidor de longo prazo. A combinação de múltiplos atrativos e margem de segurança positiva sugere potencial de valorização."
    elif score >= 40:
        txt_persp = f"Pontuação de {score}% — o ativo está em zona neutra. Pode ser interessante monitorar e aguardar um ponto de entrada mais favorável ou uma melhora nos fundamentos."
    else:
        txt_persp = f"Pontuação de {score}% indica que os fundamentos atuais não justificam o preço pedido. Não necessariamente uma empresa ruim — apenas o momento de entrada pode não ser o mais adequado."

    return {
        "empresa":     txt_empresa,
        "preco":       txt_preco,
        "atencao":     txt_atencao,
        "perspectiva": txt_persp,
    }



def analisar_qualitativa(ticker, empresa, setor, dados):
    """Análise qualitativa local — 5 critérios baseados nos dados disponíveis"""

    roe       = dados.get("roe", 0)
    dy        = dados.get("dy", 0)
    marg_liq  = dados.get("marg_liq", 0)
    cresc_5a  = dados.get("cresc_5a", 0)
    div_patrim= dados.get("div_patrim", 0)
    liq_corr  = dados.get("liq_corr", 0)
    pvp       = dados.get("pvp", 0)
    pl        = dados.get("pl", 0)
    # Usa mapa de tickers como fallback para setor
    if (not setor or setor == "—") and ticker in TICKER_SETOR_MAP:
        setor = TICKER_SETOR_MAP[ticker.upper()]
    setor_l = setor.lower() if setor and setor != "—" else ""

    def nivel(nota):
        return "FORTE" if nota >= 14 else "FRACO" if nota <= 7 else "MÉDIO"

    criterios = []

    # ── 1. Vantagem Competitiva (Moat) ──
    # Proxy: ROE alto sustentado + margem alta = moat provável
    if roe >= 20 and marg_liq >= 15:
        n1, j1 = 17, f"ROE de {roe:.1f}% e margem líquida de {marg_liq:.1f}% sugerem vantagem competitiva relevante. Empresa consegue manter rentabilidade acima da média do mercado."
    elif roe >= 15 and marg_liq >= 8:
        n1, j1 = 14, f"ROE de {roe:.1f}% indica rentabilidade sólida, com alguma vantagem competitiva. Margem de {marg_liq:.1f}% é satisfatória para o setor."
    elif roe >= 10:
        n1, j1 = 10, f"ROE de {roe:.1f}% sugere vantagem competitiva moderada. Empresa rentável mas sem diferencial muito destacado."
    else:
        n1, j1 = 5, f"ROE de {roe:.1f}% indica dificuldade em manter vantagem competitiva consistente. Rentabilidade abaixo do esperado."
    # Bônus: concessão/monopólio por setor
    if any(x in setor_l for x in ["saneam", "energia", "elétri", "eletri", "gás", "gas", "água", "agua"]):
        n1 = min(20, n1 + 3)
        j1 += " Atua em setor de concessão/infraestrutura, o que confere barreira de entrada natural."
    elif any(x in setor_l for x in ["banco", "financ"]):
        n1 = min(20, n1 + 2)
        j1 += " Setor bancário possui barreiras regulatórias que protegem os players estabelecidos."
    criterios.append({"nome": "Vantagem Competitiva (Moat)", "nota": n1, "nivel": nivel(n1), "justificativa": j1})

    # ── 2. Previsibilidade de Receita ──
    if any(x in setor_l for x in ["saneam", "energia", "elétri", "eletri", "gás", "gas", "água", "agua", "telecom"]):
        n2, j2 = 17, "Receita altamente previsível por contrato de concessão ou tarifa regulada. Fluxo de caixa estável e recorrente."
    elif any(x in setor_l for x in ["banco", "financ", "seguro"]):
        n2, j2 = 14, "Receita financeira tende a ser recorrente, embora sujeita a ciclos de crédito e spreads. Previsibilidade moderada-alta."
    elif any(x in setor_l for x in ["petró", "petro", "minera", "sider", "celulose", "papel", "agro"]):
        n2, j2 = 7, "Setor cíclico com receita atrelada a commodities. Alta volatilidade de preços reduz previsibilidade."
    elif cresc_5a > 5 and marg_liq > 5:
        n2, j2 = 13, f"Crescimento de receita de {cresc_5a:.1f}% ao ano sugere demanda consistente. Previsibilidade razoável."
    else:
        n2, j2 = 10, "Previsibilidade de receita moderada. Depende do ciclo econômico e da demanda do setor."
    criterios.append({"nome": "Previsibilidade de Receita", "nota": n2, "nivel": nivel(n2), "justificativa": j2})

    # ── 3. Gestão e Governança ──
    # Proxy: DY consistente + crescimento = gestão alocando bem capital
    if dy >= 5 and cresc_5a > 0 and div_patrim < 1.0:
        n3, j3 = 16, f"Dividend yield de {dy:.1f}% com crescimento positivo e endividamento controlado sugerem gestão disciplinada na alocação de capital."
    elif dy >= 3 and div_patrim < 1.5:
        n3, j3 = 13, f"Pagamento de dividendos de {dy:.1f}% e endividamento moderado indicam gestão financeira responsável."
    elif div_patrim > 2.0:
        n3, j3 = 6, f"Endividamento elevado ({div_patrim:.1f}x patrimônio) pode indicar gestão agressiva ou necessidade de capital. Ponto de atenção relevante."
    else:
        n3, j3 = 10, "Governança aparentemente adequada, sem sinais claros de má alocação de capital nos dados disponíveis."
    criterios.append({"nome": "Gestão e Governança", "nota": n3, "nivel": nivel(n3), "justificativa": j3})

    # ── 4. Posição no Setor ──
    # Proxy: margem + ROE acima da média = posição de destaque
    if roe >= 18 and marg_liq >= 12:
        n4, j4 = 17, f"ROE de {roe:.1f}% e margem de {marg_liq:.1f}% sugerem posição de liderança ou destaque no setor. Empresa captura valor acima dos concorrentes."
    elif roe >= 12 and marg_liq >= 6:
        n4, j4 = 13, f"Indicadores de {roe:.1f}% ROE e {marg_liq:.1f}% de margem indicam posição competitiva sólida no setor."
    elif roe >= 8:
        n4, j4 = 9, f"ROE de {roe:.1f}% indica posição intermediária no setor. Empresa competitiva mas sem grande diferencial."
    else:
        n4, j4 = 5, f"ROE de {roe:.1f}% sugere posição fraca no setor ou fase de reestruturação. Monitorar evolução dos resultados."
    criterios.append({"nome": "Posição no Setor", "nota": n4, "nivel": nivel(n4), "justificativa": j4})

    # ── 5. Risco Regulatório/Político ──
    if any(x in setor_l for x in ["saneam", "energia", "elétri", "eletri", "gás", "gas", "água", "agua"]):
        n5, j5 = 10, "Setor regulado oferece estabilidade tarifária mas expõe a empresa a revisões de concessão e interferência política. Risco moderado."
    elif any(x in setor_l for x in ["banco", "financ"]):
        n5, j5 = 11, "Setor bancário é fortemente regulado pelo Banco Central, o que garante estabilidade mas também impõe restrições operacionais."
    elif any(x in setor_l for x in ["petró", "petro", "minera"]):
        n5, j5 = 8, "Setor sujeito a royalties, regulação ambiental e interferência governamental. Risco regulatório/político relevante."
    elif any(x in setor_l for x in ["saúde", "saude", "pharma", "farm"]):
        n5, j5 = 9, "Setor sujeito a regulação da ANVISA e políticas de saúde pública. Risco moderado mas gerenciável."
    else:
        n5, j5 = 14, "Setor com baixa exposição regulatória direta. Risco político/regulatório controlado para o perfil da empresa."
    criterios.append({"nome": "Risco Regulatório/Político", "nota": n5, "nivel": nivel(n5), "justificativa": j5})

    score_qual = n1 + n2 + n3 + n4 + n5

    # ── Resumo ──
    pontos_fortes = [c["nome"] for c in criterios if c["nota"] >= 14]
    pontos_fracos = [c["nome"] for c in criterios if c["nota"] <= 7]

    if score_qual >= 70:
        resumo = f"{empresa} apresenta perfil qualitativo sólido (score {score_qual}/100). "
        resumo += f"Destaca-se em: {', '.join(pontos_fortes)}. " if pontos_fortes else ""
        resumo += "Para o investidor de longo prazo, a combinação de fundamentos qualitativos e quantitativos favoráveis representa uma oportunidade interessante de alocação."
    elif score_qual >= 50:
        resumo = f"{empresa} apresenta perfil qualitativo equilibrado (score {score_qual}/100). "
        resumo += f"Pontos fortes: {', '.join(pontos_fortes)}. " if pontos_fortes else ""
        resumo += f"Pontos de atenção: {', '.join(pontos_fracos)}. " if pontos_fracos else ""
        resumo += "Empresa adequada para investidores que buscam equilíbrio entre risco e retorno."
    else:
        resumo = f"{empresa} apresenta perfil qualitativo com pontos de atenção relevantes (score {score_qual}/100). "
        resumo += f"Principais fragilidades: {', '.join(pontos_fracos)}. " if pontos_fracos else ""
        resumo += "Recomenda-se análise mais aprofundada dos balanços antes de qualquer decisão de investimento."

    return {
        "criterios": criterios,
        "score_qualitativo": score_qual,
        "resumo": resumo
    }


# ─── Contextos Setoriais ─────────────────────────────────────────────────────
# Influência do dólar por setor: 'positivo', 'negativo', 'neutro'
DOLAR_INFLUENCIA = {
    "concessoes":  ("neutro",   "Impacto neutro — receitas em BRL, insumos parcialmente importados."),
    "portos":      ("positivo", "Dólar alto aumenta volume e receita de exportações em reais."),
    "bancos":      ("neutro",   "Impacto indireto — dólar alto pressiona tomadores de crédito em USD."),
    "agro":        ("positivo", "Commodities cotadas em USD — dólar alto eleva receita em reais."),
    "energia":     ("negativo", "Equipamentos importados e dívidas em USD encarecem com dólar alto."),
    "saneamento":  ("negativo", "Insumos e equipamentos importados ficam mais caros."),
    "varejo":      ("negativo", "Produtos importados encarecem, pressionando margens e consumo."),
    "logistica":   ("negativo", "Veículos, peças e equipamentos importados sobem com dólar."),
    "mineracao":   ("positivo", "Minério e metais cotados em USD — dólar alto eleva receita em reais."),
    "petroleo":    ("positivo", "Petróleo cotado em USD — dólar alto beneficia receitas em reais."),
    "construcao":  ("negativo", "Aço, cobre e equipamentos importados encarecem."),
    "saude":       ("negativo", "Medicamentos e equipamentos médicos importados ficam mais caros."),
    "telecom":     ("negativo", "Infraestrutura e equipamentos de tecnologia importados sobem."),
}

CONTEXTOS_SETORIAIS = {
    "concessoes": {
        "nome": "Concessões Rodoviárias",
        "status": "FAVORÁVEL",
        "cor": "verde",
        "emoji": "🟢",
        "keywords": ["concess","rodov","autopista","pedágio","pedagio","autoestrada"],
        "texto": "Superciclo de concessões em curso. Pipeline de R$148bi em leilões previstos para 2026, com 13-14 novos contratos. Selic em queda gradual reduz custo de capital das concessionárias. Dólar alto favorece corredores de exportação. Risco: atrasos em leilões e pressão de insumos (asfalto, mão de obra)."
    },
    "portos": {
        "nome": "Portos / Hidrovias",
        "status": "FAVORÁVEL",
        "cor": "verde",
        "emoji": "🟢",
        "keywords": ["porto","hidrovia","terminal","navegação","navegacao","logíst","logist","transporte aquav"],
        "texto": "Safra 2025/26 acima da média histórica impulsiona movimentação portuária. Pico de escoamento de soja e milho entre janeiro e maio. Dólar elevado aumenta receita em reais das operações ligadas à exportação. Risco: congestionamento operacional e dependência climática."
    },
    "bancos": {
        "nome": "Bancos / Financeiro",
        "status": "NEUTRO",
        "cor": "amarelo",
        "emoji": "🟡",
        "keywords": ["banco","financ","crédito","credito","seguro","capital","previdên","previdenc"],
        "texto": "Crédito rural aquecido com safra forte, mas Selic ainda elevada pressiona inadimplência pessoa física e PMEs. Spread bancário sustentado. LCA e CPR com alta demanda. Bancos públicos com exposição maior ao risco político. Risco: deterioração fiscal e aumento de calotes no agro em caso de queda de preços de commodities."
    },
    "agro": {
        "nome": "Agro / Commodities Agrícolas",
        "status": "FAVORÁVEL",
        "cor": "verde",
        "emoji": "🟢",
        "keywords": ["agro","agrícol","agricol","aliment","grão","grao","soja","milho","cana","açúcar","acucar","frigoríf","frigorif","proteína","proteina","maquina","máquina","equipamento","implemento"],
        "texto": "Safra 2025/26 de soja projetada entre 165-170 milhões de toneladas. Dólar acima de R$5,40 favorece exportadores. Preços internacionais de milho e soja em patamar sustentável. Atenção ao La Niña residual no Sul e ao impacto de tarifas americanas no fluxo global de grãos. Momento positivo para produtores e empresas do agro."
    },
    "energia": {
        "nome": "Energia Elétrica",
        "status": "NEUTRO",
        "cor": "amarelo",
        "emoji": "🟡",
        "keywords": ["energ","elétric","electric","geraç","geracao","transmiss","distribui","eólica","eolica","solar","hidrelét","hidrelet"],
        "texto": "Reservatórios em nível adequado após chuvas do verão. Geração hídrica normalizada reduz pressão sobre térmicas e tarifas. Revisões tarifárias da ANEEL em curso para distribuidoras. Expansão de energia solar e eólica pressiona margens de transmissoras tradicionais. Risco: estiagem no segundo semestre e interferência tarifária política."
    },
    "saneamento": {
        "nome": "Saneamento",
        "status": "FAVORÁVEL",
        "cor": "verde",
        "emoji": "🟢",
        "keywords": ["saneam","água","agua","esgoto","resíduo","residuo","ambiental"],
        "texto": "Marco Legal do Saneamento acelerando privatizações e concessões. Meta de universalização até 2033 exige R$700bi em investimentos. Pipeline robusto de leilões estaduais e municipais. Selic em queda beneficia financiamento de longo prazo. Risco: execução lenta por parte dos municípios e judicialização de contratos."
    },
    "varejo": {
        "nome": "Varejo",
        "status": "PRESSÃO",
        "cor": "vermelho",
        "emoji": "🔴",
        "keywords": ["varejo","comercio","comércio","supermercado","vestuário","vestuario","moda","farmácia","farmacia","eletrônic","eletronic","e-commerce"],
        "texto": "Inflação de alimentos pressionando poder de compra das famílias de baixa renda. Juros do rotativo ainda elevados limitam consumo. Inadimplência do consumidor acima da média histórica. Programas sociais sustentam consumo mínimo mas não impulsionam crescimento. Risco: piora fiscal e corte de transferências governamentais."
    },
    "logistica": {
        "nome": "Logística / Galpões",
        "status": "FAVORÁVEL",
        "cor": "verde",
        "emoji": "🟢",
        "keywords": ["galpão","galpao","armazém","armazem","logíst","logist","distribui","fulfillment","multimodal"],
        "texto": "E-commerce e agro sustentam alta demanda por galpões logísticos de alto padrão. Taxa de vacância em mínimas históricas nas regiões Sul e Sudeste. Expansão para o Centro-Oeste acompanhando o agro. Dólar alto encarece construção (aço, equipamentos importados). Risco: desaceleração do e-commerce e oversupply em regiões secundárias."
    },
    "mineracao": {
        "nome": "Mineração",
        "status": "NEUTRO",
        "cor": "amarelo",
        "emoji": "🟡",
        "keywords": ["miner","siderurgi","metalurgi","ferro","aço","aco","alumínio","aluminio","cobre","níquel","niquel"],
        "texto": "Preço do minério de ferro pressionado pela demanda chinesa abaixo do esperado. Cobre e níquel com perspectiva positiva pela transição energética global. Dólar alto favorece receitas em reais mas custos operacionais sobem. Risco: desaceleração da China, regulação ambiental crescente e instabilidade em regiões de extração."
    },
    "petroleo": {
        "nome": "Petróleo / Petroquímica",
        "status": "NEUTRO",
        "cor": "amarelo",
        "emoji": "🟡",
        "keywords": ["petróleo","petroleo","petroquím","petroquim","refinaria","combustív","combustiv","óleo","oleo","gás","gas natural"],
        "texto": "Preço do Brent em faixa de US$70-80, sustentado por cortes da OPEP+ mas pressionado por crescimento global moderado. Petrobras com geração de caixa robusta e dividendos elevados. Risco político de interferência na política de preços e dividendos. Downstream pressionado por margens de refino apertadas e concorrência de importados."
    },
    "construcao": {
        "nome": "Construção Civil / Imóveis",
        "status": "NEUTRO",
        "cor": "amarelo",
        "emoji": "🟡",
        "keywords": ["constru","imóvel","imovel","incorpora","habitaç","habitac","shopping","real estate","edifica"],
        "texto": "Programa Minha Casa Minha Vida aquecido no segmento econômico. Alto padrão pressionado por juros elevados e distrato. Custo de construção (INCC) ainda acima da inflação. Vacância em shoppings estável. Risco: Selic alta prolongada e desaceleração do crédito imobiliário."
    },
    "saude": {
        "nome": "Saúde",
        "status": "NEUTRO",
        "cor": "amarelo",
        "emoji": "🟡",
        "keywords": ["saúde","saude","hospital","clínica","clinica","diagnóst","diagnost","pharma","farmacêut","farmaceut","plano de saúde","plano de saude"],
        "texto": "Setor defensivo com demanda resiliente. Inflação médica (IPCA saúde) persistente pressiona custos de operadoras. Regulação da ANS em revisão. Telemedicina e diagnósticos digitais avançando. Risco: sinistralidade elevada em planos de saúde e concentração de mercado atraindo atenção regulatória."
    },
    "telecom": {
        "nome": "Telecomunicações",
        "status": "NEUTRO",
        "cor": "amarelo",
        "emoji": "🟡",
        "keywords": ["telecom","telefon","comunicaç","comunicac","internet","fibra","5g","banda larga","tv por assinatura"],
        "texto": "Expansão de fibra óptica e 5G mantém investimentos elevados. Consolidação do setor reduz competição e sustenta ARPU. Demanda corporativa por conectividade cresce com digitalização. Risco: regulação da Anatel, inadimplência de clientes pessoa física e custo de espectro."
    },
}

# Mapa manual de tickers → setor (fallback quando Fundamentus não retorna setor)
TICKER_SETOR_MAP = {
    # Petróleo
    "PETR4":"Petróleo e Gás","PETR3":"Petróleo e Gás","RECV3":"Petróleo e Gás",
    "PRIO3":"Petróleo e Gás","RRRP3":"Petróleo e Gás","CSAN3":"Petróleo e Gás",
    # Mineração
    "VALE3":"Mineração","CSNA3":"Siderurgia","GGBR4":"Siderurgia","USIM5":"Siderurgia",
    "BRAP4":"Mineração","CBAV3":"Mineração","CMIN3":"Mineração",
    # Bancos
    "ITUB4":"Bancos","ITUB3":"Bancos","BBDC4":"Bancos","BBDC3":"Bancos",
    "BBAS3":"Bancos","SANB4":"Bancos","SANB3":"Bancos","SANB11":"Bancos",
    "BRSR6":"Bancos","BPAC11":"Bancos","ABCB4":"Bancos","BMGB4":"Bancos",
    # Energia
    "EGIE3":"Energia Elétrica","ENGI11":"Energia Elétrica","TAEE11":"Energia Elétrica",
    "CPFE3":"Energia Elétrica","CMIG4":"Energia Elétrica","CMIG3":"Energia Elétrica",
    "ELET3":"Energia Elétrica","ELET6":"Energia Elétrica","AURE3":"Energia Elétrica",
    "CPLE6":"Energia Elétrica","CESP6":"Energia Elétrica","TRPL4":"Energia Elétrica",
    "ENEV3":"Energia Elétrica","EQTL3":"Energia Elétrica","NEOE3":"Energia Elétrica",
    # Saneamento
    "SAPR4":"Saneamento","SAPR3":"Saneamento","SAPR11":"Saneamento",
    "SBSP3":"Saneamento","CSMG3":"Saneamento","FESA4":"Saneamento",
    # Concessões Rodoviárias
    "ECOR3":"Concessões Rodoviárias","CCRO3":"Concessões Rodoviárias",
    "TIMS3":"Concessões Rodoviárias","RDNI3":"Concessões Rodoviárias",
    # Portos / Hidrovias / Transporte
    "HBSA3":"Transporte Hidroviário","TPIS3":"Transporte Hidroviário",
    "LOGN3":"Logística","RAIL3":"Logística","JSLG3":"Logística",
    "TGMA3":"Logística","VAMO3":"Logística","POMO4":"Logística",
    # Agro
    "SLCE3":"Agronegócio","AGRO3":"Agronegócio","SMTO3":"Agronegócio",
    "TTEN3":"Agronegócio","CAML3":"Agronegócio","BEEF3":"Agronegócio",
    "MRFG3":"Agronegócio","JBSS3":"Agronegócio","BRFS3":"Agronegócio",
    "MFRG3":"Agronegócio","CSLT3":"Agronegócio",
    # Varejo
    "MGLU3":"Varejo","VIIA3":"Varejo","AMER3":"Varejo","LREN3":"Varejo",
    "HGTX3":"Varejo","SOMA3":"Varejo","ALPA4":"Varejo","CEAB3":"Varejo",
    "PCAR3":"Varejo Alimentar","ASAI3":"Varejo Alimentar","CRFB3":"Varejo Alimentar",
    # Saúde
    "RDOR3":"Saúde","HAPV3":"Saúde","GNDI3":"Saúde","FLRY3":"Saúde",
    "DASA3":"Saúde","QUAL3":"Saúde","PARD3":"Saúde","ONCO3":"Saúde",
    # Telecom
    "VIVT3":"Telecomunicações","TIMS3":"Telecomunicações","OIBR3":"Telecomunicações",
    # Construção
    "MRVE3":"Construção Civil","CYRE3":"Construção Civil","EVEN3":"Construção Civil",
    "EZTC3":"Construção Civil","DIRR3":"Construção Civil","TEND3":"Construção Civil",
    "MULT3":"Shopping","IGTI11":"Shopping","BRML3":"Shopping",
    # Papel/Celulose
    "SUZB3":"Papel e Celulose","KLBN11":"Papel e Celulose","RANI3":"Papel e Celulose",
    # Máquinas e Equipamentos Agrícolas
    "WEGE3":"Máquinas Industriais","WEGE":"Máquinas Industriais","KEPL3":"Máquinas Agrícolas","RAIN3":"Máquinas Agrícolas","FRAS3":"Máquinas Agrícolas",
    "AGXY3":"Máquinas Agrícolas","RCSL4":"Máquinas Agrícolas",
    # Transportes diversos
    "AZUL4":"Transporte Aéreo","GOLL4":"Transporte Aéreo","EMBR3":"Aeronáutico",
    "RENT3":"Locação de Veículos","MOVI3":"Locação de Veículos","VAMO3":"Locação de Veículos",
    # Tecnologia
    "TOTS3":"Tecnologia","LWSA3":"Tecnologia","POSI3":"Tecnologia","INTB3":"Tecnologia",
    "CASH3":"Tecnologia","IFCM3":"Tecnologia","DESK3":"Tecnologia",
    # Seguros
    "BBSE3":"Seguros","IRBR3":"Seguros","PSSA3":"Seguros","SULA11":"Seguros",
    # FIIs Logística
    "XPLG11":"Logística","HGLG11":"Logística","BRCO11":"Logística","LVBI11":"Logística",
}

def detectar_contexto_setor(setor, ticker=""):
    """Detecta o contexto setorial baseado no setor da empresa"""
    # Fallback: usar mapa de tickers se setor não disponível
    setor_efetivo = setor
    if (not setor or setor == "—") and ticker:
        setor_efetivo = TICKER_SETOR_MAP.get(ticker.upper(), "—")
    if not setor_efetivo or setor_efetivo == "—":
        return None
    setor_l = setor_efetivo.lower()
    # Remove acentos para comparação
    setor_norm = setor_l
    for a, b in [("ã","a"),("â","a"),("á","a"),("à","a"),("é","e"),("ê","e"),
                 ("í","i"),("ó","o"),("ô","o"),("õ","o"),("ú","u"),("ç","c")]:
        setor_norm = setor_norm.replace(a, b)

    for key, ctx in CONTEXTOS_SETORIAIS.items():
        for kw in ctx["keywords"]:
            kw_norm = kw
            for a, b in [("ã","a"),("â","a"),("á","a"),("à","a"),("é","e"),("ê","e"),
                         ("í","i"),("ó","o"),("ô","o"),("õ","o"),("ú","u"),("ç","c")]:
                kw_norm = kw_norm.replace(a, b)
            if kw_norm in setor_norm:
                result = dict(ctx)
                dolar_info = DOLAR_INFLUENCIA.get(key, ("neutro", "Impacto do dólar não mapeado para este setor."))
                result["dolar_tipo"] = dolar_info[0]
                result["dolar_texto"] = dolar_info[1]
                return result
    return None

# ─── Servidor HTTP ────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  → {args[1]}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type",  "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urlparse(self.path)

        # Serve o frontend
        if p.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type",   "text/html; charset=utf-8")
            self.send_header("Content-Length",  len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        # API de análise
        if p.path == "/analisar":
            ticker = parse_qs(p.query).get("ticker", [""])[0].strip().upper()
            if not ticker:
                self.send_json({"erro": "Ticker não informado"}, 400)
                return
            try:
                print(f"\n🔍 Analisando {ticker}...")

                # 1. Fundamentus (dados principais)
                d = buscar_fundamentus(ticker)

                # Só rejeita se a página veio vazia (ticker realmente não existe)
                # _html_valido=False significa que o HTML tinha menos de 1000 chars
                # ou continha "Nenhum papel encontrado"
                if d.get("_pagina_invalida"):
                    self.send_json({"erro": f"Ticker '{ticker}' não encontrado. Verifique se está correto."})
                    return

                # 2. Investidor10 (dados complementares)
                extra = buscar_investidor10(ticker)
                # Complementa com média quando Fundamentus não trouxe
                for campo_i10, campo_fund in [("pl_i10","pl"),("dy_i10","dy"),("roe_i10","roe")]:
                    if extra.get(campo_i10) and d.get(campo_fund, 0) == 0:
                        d[campo_fund] = extra[campo_i10]
                if extra.get("payout"):    d["payout"]      = extra["payout"]
                if extra.get("cresc_lucro"): d["cresc_lucro"] = extra["cresc_lucro"]

                # 3. Variações de mercado
                d["var_mes"]      = buscar_var(f"{ticker}.SA")
                d["var_ibov_mes"] = buscar_var("%5EBVSP")
                d["ipca_12m"]     = buscar_ipca()
                d["dolar"]        = buscar_dolar()

                # 4. Tipo de empresa — usa setor real ou mapa de tickers
                setor_raw = d.get("setor", "")
                if not setor_raw or setor_raw == "—":
                    setor_raw = TICKER_SETOR_MAP.get(ticker, "")
                setor_low = setor_raw.lower()
                # ── Perfil da empresa: valor / crescimento / dividendos / banco / util / cicl ──
                roe_val    = d.get("roe", 0)
                dy_val     = d.get("dy", 0)
                pl_val     = d.get("pl", 0)
                cresc_val  = d.get("cresc_5a", 0)

                if any(x in setor_low for x in ["banco","financ","seguro","crédit","credito"]):
                    tipo = "banco"
                elif any(x in setor_low for x in ["energia","elétri","eletri","saneam","água","agua","gás","gas","concess","rodovi","ferrovi"]):
                    tipo = "util"
                elif any(x in setor_low for x in ["petró","petro","minera","sider","celulose","papel","metalur"]):
                    tipo = "cicl"
                elif roe_val >= 20 and pl_val > 18:
                    # ROE alto sustentado + mercado paga prêmio = CRESCIMENTO
                    # (não depende de cresc_5a que frequentemente vem zerado do Fundamentus)
                    tipo = "cresc"
                elif dy_val >= 6 and pl_val < 15:
                    # Alto DY + múltiplo baixo = foco em dividendos
                    tipo = "div"
                elif pl_val < 12 and d.get("pvp", 0) < 1.2:
                    # Múltiplos muito baixos = valor puro
                    tipo = "valor"
                else:
                    tipo = "geral"

                # Perfil label para exibição no frontend
                perfil_labels = {
                    "banco":  ("🏦", "BANCO/FINANCEIRO",  "Avaliado por ROE, P/VP e qualidade da carteira"),
                    "util":   ("⚡", "UTILIDADE/CONCESSÃO","Avaliado por DY, estabilidade e P/L regulado"),
                    "cicl":   ("⛏",  "CÍCLICO/COMMODITY",  "Avaliado com cautela em múltiplos — lucro varia com ciclo"),
                    "cresc":  ("🚀", "CRESCIMENTO",         "Avaliado por ROE, crescimento e qualidade — P/L alto é esperado"),
                    "div":    ("💰", "DIVIDENDOS",          "Avaliado por DY sustentável, Bazin e previsibilidade"),
                    "valor":  ("💎", "VALOR",               "Avaliado por margem de segurança e múltiplos baixos"),
                    "geral":  ("📊", "GERAL",               "Análise padrão equilibrada"),
                }
                perfil_info = perfil_labels.get(tipo, perfil_labels["geral"])

                # 5. Crescimento estimado (usa dados reais se disponível)
                cresc_raw = d.get("cresc_lucro", d.get("cresc_5a", 5)) or 5
                # Cap de crescimento por tipo: cíclicas e petróleo limitam a 8%
                if tipo in ("cicl",):
                    cresc = max(2, min(8, cresc_raw))
                elif tipo == "banco":
                    cresc = max(3, min(12, cresc_raw))
                else:
                    cresc = max(3, min(20, cresc_raw))

                # 6. Preço justo
                pj = calcular_preco_justo(d, cresc, tipo)

                # 7. Score e critérios
                score, criterios = calcular_score(d, pj, tipo)

                # 8. Análise textual
                analise = gerar_analise(d, pj, score, tipo)

                # 9. Análise qualitativa via Claude API
                print(f"  🤖 Gerando análise qualitativa...")
                qualitativa = analisar_qualitativa(
                    ticker,
                    d.get("empresa", ticker),
                    d.get("setor", "—"),
                    d
                )

                print(f"  ✅ R${d['preco']:.2f} | P/L {d['pl']:.1f}x | ROE {d['roe']:.1f}% | Score {score}%")

                self.send_json({
                    "ticker":  ticker,
                    "empresa": d.get("empresa", ticker),
                    "setor":   d.get("setor", "—"),
                    "dados": {
                        "preco":       d.get("preco", 0),
                        "pl":          d.get("pl", 0),
                        "pvp":         d.get("pvp", 0),
                        "roe":         d.get("roe", 0),
                        "dy":          d.get("dy", 0),
                        "lpa":         d.get("lpa", 0),
                        "vpa":         d.get("vpa", 0),
                        "dividendo12m":d.get("dividendo12m", 0),
                        "var_mes":     d.get("var_mes", 0),
                        "var_ibov_mes":d.get("var_ibov_mes", 0),
                        "ipca_12m":    d.get("ipca_12m", 0),
                        "dolar":       d.get("dolar", 0),
                        "marg_liq":    d.get("marg_liq", 0),
                        "div_patrim":  d.get("div_patrim", 0),
                    },
                    "precos_justos": pj,
                    "score":         score,
                    "criterios":     criterios,
                    "analise":       analise,
                    "qualitativa":   qualitativa,
                    "contexto_setor": detectar_contexto_setor(d.get("setor","—"), ticker),
                    "perfil":         {"tipo": tipo, "emoji": perfil_info[0], "label": perfil_info[1], "desc": perfil_info[2]},
                    "score_final":    round(score * 0.6 + qualitativa.get("score_qualitativo", 0) * 0.4, 1),
                    "preco_alvo":     pj.get("media", 0),
                    "sinal":          (
                        "compra" if score >= 70 and pj.get("margem", 0) > -5 else
                        "compra" if score >= 65 and pj.get("margem", 0) > 10 else
                        "evitar" if score < 45 else
                        "evitar" if pj.get("margem", 0) < -25 else
                        "neutro"
                    ),
                    "setor_detectado": d.get("setor","—") if d.get("setor","—") != "—" else TICKER_SETOR_MAP.get(ticker.upper(),"—"),
                    "ticker":         ticker.upper(),
                })

            except URLError as e:
                self.send_json({"erro": f"Erro de conexão: {e}. Verifique sua internet."})
            except Exception as e:
                import traceback; traceback.print_exc()
                self.send_json({"erro": f"Erro ao processar {ticker}: {str(e)}"})
            return

        self.send_response(404)
        self.end_headers()


# ─── Main ─────────────────────────────────────────────────────────────────────
def iniciar():
    print("\n" + "="*52)
    print("  📊  QUANTTECH VALOR JUSTO")
    print("="*52)
    print(f"  🌐  Acesse: http://0.0.0.0:{PORT}")
    print("="*52 + "\n")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Encerrado.")

# Compatibilidade com Gunicorn (Railway)
class _AppWSGI:
    def __call__(self, environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b'OK']

app = _AppWSGI()

# Roda tanto via `python app.py` quanto via Gunicorn
if __name__ == '__main__':
    iniciar()
else:
    import threading
    threading.Thread(target=iniciar, daemon=True).start()
