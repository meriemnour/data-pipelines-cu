# Terraform Assignment: First Webserver (Local)
# Deploys a Docker container serving a simple HTML page on localhost:8080

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

provider "docker" {}

resource "docker_image" "nginx" {
  name = "nginx:alpine"
}

resource "local_file" "index_html" {
  content  = <<-HTML
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>My First Terraform Webserver</title>
      <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
      <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
          --bg: #060612; --surface: #0e0e1f; --card: #13132a;
          --accent: #00ff88; --accent2: #00aaff; --accent3: #ff6b6b;
          --text: #e8e8f8; --muted: #4a4a70; --border: rgba(255,255,255,0.06);
        }
        body {
          background: var(--bg); color: var(--text);
          font-family: 'Space Mono', monospace;
          min-height: 100vh; display: flex;
          align-items: center; justify-content: center; overflow-x: hidden;
        }
        body::before {
          content: ''; position: fixed; inset: 0;
          background:
            radial-gradient(ellipse 80% 50% at 20% 50%, rgba(0,255,136,0.05) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 80% 20%, rgba(0,170,255,0.05) 0%, transparent 60%),
            radial-gradient(ellipse 50% 60% at 60% 80%, rgba(124,58,237,0.05) 0%, transparent 60%);
          z-index: 0; animation: bgPulse 8s ease-in-out infinite alternate;
        }
        body::after {
          content: ''; position: fixed; inset: 0;
          background-image:
            linear-gradient(rgba(0,255,136,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,255,136,0.025) 1px, transparent 1px);
          background-size: 48px 48px; z-index: 0;
          animation: gridScroll 25s linear infinite;
        }
        @keyframes bgPulse { from { opacity:.5; } to { opacity:1; } }
        @keyframes gridScroll { from { transform:translateY(0); } to { transform:translateY(48px); } }
        @keyframes fadeDown { from { opacity:0; transform:translateY(-14px); } to { opacity:1; transform:translateY(0); } }
        @keyframes blink { 0%,100% { opacity:1; } 50% { opacity:.2; } }
        .wrapper { position:relative; z-index:1; width:100%; max-width:780px; padding:2rem 1.5rem; }
        .topbar { display:flex; align-items:center; justify-content:space-between; margin-bottom:3rem; animation:fadeDown .5s ease both; }
        .logo { font-family:'Syne',sans-serif; font-size:.8rem; font-weight:800; letter-spacing:.2em; text-transform:uppercase; color:var(--accent); }
        .status-pill { display:flex; align-items:center; gap:.5rem; background:rgba(0,255,136,.08); border:1px solid rgba(0,255,136,.2); padding:.35rem .9rem; border-radius:100px; font-size:.7rem; color:var(--accent); letter-spacing:.1em; }
        .status-dot { width:6px; height:6px; border-radius:50%; background:var(--accent); box-shadow:0 0 8px var(--accent); animation:blink 1.5s infinite; }
        .hero { margin-bottom:3rem; animation:fadeDown .5s ease .1s both; }
        .eyebrow { font-size:.7rem; letter-spacing:.25em; text-transform:uppercase; color:var(--muted); margin-bottom:1rem; }
        h1 { font-family:'Syne',sans-serif; font-size:clamp(2.8rem,9vw,5.5rem); font-weight:800; line-height:1; margin-bottom:1.5rem; }
        h1 .line1 { color:var(--text); }
        h1 .line2 { background:linear-gradient(90deg,var(--accent),var(--accent2)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
        .desc { color:var(--muted); font-size:.82rem; line-height:1.9; max-width:480px; }
        .cards { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-bottom:1.5rem; animation:fadeDown .5s ease .2s both; }
        .card { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:1.2rem; transition:border-color .2s,transform .2s; }
        .card:hover { border-color:rgba(0,255,136,.2); transform:translateY(-3px); }
        .card-icon { font-size:1.4rem; margin-bottom:.7rem; }
        .card-label { font-size:.65rem; letter-spacing:.15em; text-transform:uppercase; color:var(--muted); margin-bottom:.3rem; }
        .card-value { font-size:.85rem; font-weight:700; color:var(--text); }
        .card-value.green { color:var(--accent); } .card-value.blue { color:var(--accent2); } .card-value.red { color:var(--accent3); }
        .url-block { background:var(--card); border:1px solid rgba(0,255,136,.15); border-radius:10px; padding:1.4rem 1.6rem; display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem; animation:fadeDown .5s ease .3s both; transition:border-color .2s,box-shadow .2s; }
        .url-block:hover { border-color:rgba(0,255,136,.35); box-shadow:0 0 30px rgba(0,255,136,.07); }
        .url-label { font-size:.65rem; letter-spacing:.15em; text-transform:uppercase; color:var(--muted); margin-bottom:.4rem; }
        .url-value { font-size:1.1rem; font-weight:700; color:var(--accent); }
        .url-badge { background:rgba(0,255,136,.1); border:1px solid rgba(0,255,136,.2); color:var(--accent); font-size:.65rem; letter-spacing:.1em; text-transform:uppercase; padding:.4rem .8rem; border-radius:4px; }
        .terminal { background:#080810; border:1px solid var(--border); border-radius:10px; overflow:hidden; animation:fadeDown .5s ease .4s both; margin-bottom:1.5rem; }
        .terminal-bar { background:var(--surface); padding:.6rem 1rem; display:flex; align-items:center; gap:.5rem; border-bottom:1px solid var(--border); }
        .dot-r{width:10px;height:10px;border-radius:50%;background:#ff5f57;}
        .dot-y{width:10px;height:10px;border-radius:50%;background:#febc2e;}
        .dot-g{width:10px;height:10px;border-radius:50%;background:#28c840;}
        .terminal-title { font-size:.7rem; color:var(--muted); margin:0 auto; letter-spacing:.1em; }
        .terminal-body { padding:1.2rem 1.5rem; font-size:.78rem; line-height:2; }
        .t-muted{color:var(--muted);} .t-green{color:var(--accent);} .t-blue{color:var(--accent2);} .t-white{color:var(--text);} .t-prompt{color:#7c3aed;}
        .footer { display:flex; justify-content:space-between; align-items:center; color:var(--muted); font-size:.68rem; letter-spacing:.08em; animation:fadeDown .5s ease .5s both; }
      </style>
    </head>
    <body>
      <div class="wrapper">
        <div class="topbar">
          <div class="logo">⬡ Terraform</div>
          <div class="status-pill"><span class="status-dot"></span>LIVE · PORT 8080</div>
        </div>
        <div class="hero">
          <div class="eyebrow">Assignment · Local Deployment</div>
          <h1><div class="line1">Hello from</div><div class="line2">Terraform!</div></h1>
          <p class="desc">This page was deployed using Terraform + Docker.<br/>nginx:alpine is serving this file on your local machine.</p>
        </div>
        <div class="cards">
          <div class="card"><div class="card-icon">🐳</div><div class="card-label">Container</div><div class="card-value blue">nginx:alpine</div></div>
          <div class="card"><div class="card-icon">⚡</div><div class="card-label">Status</div><div class="card-value green">Running</div></div>
          <div class="card"><div class="card-icon">📦</div><div class="card-label">Resources</div><div class="card-value red">3 added</div></div>
        </div>
        <div class="url-block">
          <div><div class="url-label">Local URL</div><div class="url-value">http://localhost:8080</div></div>
          <div class="url-badge">✓ Reachable</div>
        </div>
        <div class="terminal">
          <div class="terminal-bar">
            <span class="dot-r"></span><span class="dot-y"></span><span class="dot-g"></span>
            <span class="terminal-title">terraform output</span>
          </div>
          <div class="terminal-body">
            <div><span class="t-prompt">❯</span> <span class="t-white">terraform apply</span></div>
            <div><span class="t-green">Apply complete!</span> <span class="t-muted">Resources: 3 added, 0 changed, 0 destroyed.</span></div>
            <div>&nbsp;</div>
            <div><span class="t-blue">Outputs:</span></div>
            <div><span class="t-muted">container_name</span> <span class="t-white">= </span><span class="t-green">"terraform-assignment-webserver"</span></div>
            <div><span class="t-muted">local_url &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span> <span class="t-white">= </span><span class="t-green">"http://localhost:8080"</span></div>
          </div>
        </div>
        <div class="footer">
          <span>Infrastructure as Code · Local Docker</span>
          <span>Terraform v1.14.6</span>
        </div>
      </div>
    </body>
    </html>
  HTML
  filename = "${path.module}/index.html"
}

resource "docker_container" "webserver" {
  image    = docker_image.nginx.image_id
  name     = "terraform-assignment-webserver"
  must_run = true

  depends_on = [local_file.index_html]

  ports {
    internal = 80
    external = 8080
  }

  volumes {
    host_path      = abspath(path.module)
    container_path = "/usr/share/nginx/html"
    read_only      = true
  }
}

output "local_url" {
  value       = "http://localhost:8080"
  description = "URL to access your deployed HTML page (local)"
}

output "container_name" {
  value       = docker_container.webserver.name
  description = "Docker container name"
}
