# Avvio in locale con Streamlit (Raccomandato)
PYTHONPATH=src streamlit run streamlit_app.py

# installare docx
pip install docxtpl python-docx

# installare pdf
curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh
tlmgr install ltxcmds infwarerr kvoptions

# installare pacchetti mancanti (pdf generator) (IN SOLO CASO DI ERRORE)
tlmgr install multirow
tlmgr install subcaption
tlmgr install titlesec
tlmgr install caption
tlmgr install hyperref
tlmgr install xcolor
tlmgr install geometry
tlmgr install enumitem
tlmgr install booktabs
tlmgr install tabularx
tlmgr install fancyvrb
tlmgr install float
tlmgr install pdfpages
tlmgr install amsmath
tlmgr install amssymb
tlmgr install amsfonts
tlmgr install amsbsy
tlmgr install amsmath
tlmgr install amssymb
tlmgr install amsfonts
tlmgr install amsbsy

# Per macOS 12 (Docker Desktop non supportato)
# Installare Colima come alternativa Docker
brew install colima
brew install qemu
colima start --runtime docker

# Poi avviare Supabase localmente
supabase start

