#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
SITE_DIR = ROOT_DIR / "_site"
TEMPLATES_DIR = ROOT_DIR / "templates"
DOCS_DIR = ROOT_DIR / "docs"

def convert_md_links(content: str) -> str:
    """Convert .md references to .html in markdown links (e.g. README.md -> index.html, file.md -> file.html)"""
    def replace_link(match):
        label = match.group(1)
        url = match.group(2)
        if url.endswith("README.md") or url.endswith("/README.md"):
            url = re.sub(r"README\.md$", "index.html", url)
        elif url.endswith(".md") and not url.startswith("http://") and not url.startswith("https://"):
            url = url[:-3] + ".html"
        return f"[{label}]({url})"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, content)

def build_site():
    print("🚀 Starting Pandoc GitHub Pages site build...")
    
    # Check if pandoc is available
    pandoc_available = shutil.which("pandoc") is not None

    if not pandoc_available:
        print("⚠️ Warning: 'pandoc' command not found in PATH.")
        print("Running in compatibility / fallback mode for local testing.")

    # Recreate _site directory
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copy CSS assets
    assets_dir = SITE_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    if (TEMPLATES_DIR / "style.css").exists():
        shutil.copy(TEMPLATES_DIR / "style.css", assets_dir / "style.css")
        print("✓ Copied style.css to _site/assets/")

    # Collect Markdown files
    md_files = []
    
    # Root README.md -> index.html
    readme_path = ROOT_DIR / "README.md"
    if readme_path.exists():
        md_files.append((readme_path, SITE_DIR / "index.html", ""))

    # files in docs/
    if DOCS_DIR.exists():
        for md_path in DOCS_DIR.glob("**/*.md"):
            rel_to_docs = md_path.relative_to(DOCS_DIR)
            out_html_path = SITE_DIR / "docs" / rel_to_docs.with_suffix(".html")
            rel_depth = len(rel_to_docs.parents)  # 1 for docs/file.md -> '../'
            relpath = "../" * rel_depth
            md_files.append((md_path, out_html_path, relpath))

    template_path = TEMPLATES_DIR / "template.html"

    # Temporary directory for preprocessed MD files
    tmp_dir = ROOT_DIR / ".build_tmp"
    tmp_dir.mkdir(exist_ok=True)

    for src_path, out_path, relpath in md_files:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read & preprocess markdown content (updating links)
        raw_md = src_path.read_text(encoding="utf-8")
        processed_md = convert_md_links(raw_md)
        
        tmp_md_path = tmp_dir / f"tmp_{src_path.name}"
        tmp_md_path.write_text(processed_md, encoding="utf-8")

        css_link = f"{relpath}assets/style.css"
        
        if pandoc_available:
            cmd = [
                "pandoc",
                str(tmp_md_path),
                "-o", str(out_path),
                "--standalone",
                "--toc",
                "--template", str(template_path),
                "--css", css_link,
                "-V", f"relpath={relpath}",
                "-f", "gfm"
            ]
            try:
                subprocess.run(cmd, check=True)
                print(f"✓ Built: {src_path.relative_to(ROOT_DIR)} -> {out_path.relative_to(ROOT_DIR)}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error compiling {src_path}: {e}")
        else:
            # Basic fallback HTML generation if pandoc is not installed
            title = src_path.stem.replace("-", " ").title()
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link rel="stylesheet" href="{css_link}">
</head>
<body>
  <header class="site-header">
    <a href="{relpath}index.html" class="site-brand">📚 GH-600 Docs</a>
    <nav class="site-nav">
      <a href="{relpath}index.html">Home</a>
      <a href="{relpath}docs/index.html">Docs</a>
    </nav>
  </header>
  <div class="layout-container">
    <main class="main-content">
      <pre>{processed_md}</pre>
    </main>
  </div>
</body>
</html>"""
            out_path.write_text(html_content, encoding="utf-8")
            print(f"✓ Built (Fallback): {src_path.relative_to(ROOT_DIR)} -> {out_path.relative_to(ROOT_DIR)}")

    # Clean up temp dir
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    print("\n🎉 Build complete! Site generated in '_site/'.")

if __name__ == "__main__":
    build_site()
