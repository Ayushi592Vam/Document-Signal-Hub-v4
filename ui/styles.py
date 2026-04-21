"""
ui/styles.py
Complete light-theme CSS injected once at app startup.
"""

GLOBAL_CSS: str = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Source+Sans+3:wght@300;400;600;700&display=swap');

:root {
    --bg:#ffffff;
    --surface:#f8f9fc;
    --s0:#f1f3f8;
    --s1:#e8ecf4;
    --s2:#dde2ee;
    --b0:#d0d6e8;
    --b1:#bcc4dc;

    --blue:#1a6fd8;--blue-lt:#4f9cf9;--blue-dk:#0f4db0;
    --blue-g:rgba(26,111,216,0.07);--blue-mid:rgba(26,111,216,0.13);
    --green:#0a9e6a;--green-lt:#34d399;--green-g:rgba(10,158,106,0.07);
    --yellow:#c99a00;--yellow-lt:#f5c842;--yellow-g:rgba(201,154,0,0.07);
    --red:#d64040;--red-lt:#f87171;--red-g:rgba(214,64,64,0.07);
    --purple:#6b3fd4;--purple-g:rgba(107,63,212,0.07);

    --t0:#0f1117;--t1:#1a1f2e;--t2:#2d3650;--t3:#4a5578;--t4:#6b7a9e;
    --font-head:'Segoe UI','Helvetica Neue',Arial,sans-serif;
    --font:'Source Sans 3','Source Sans Pro','Segoe UI',system-ui,sans-serif;
    --mono:'JetBrains Mono','Cascadia Code','Consolas',monospace;
    --sz-xl:16px;--sz-lg:15px;--sz-body:14px;--sz-sm:13px;--sz-xs:12px;
    --shadow-sm:0 1px 4px rgba(30,50,100,.10),0 0 1px rgba(26,111,216,.06);
    --shadow:0 4px 16px rgba(30,50,100,.13),0 0 2px rgba(26,111,216,.08);
    --shadow-lg:0 8px 32px rgba(30,50,100,.18),0 0 4px rgba(26,111,216,.10);
    --radius-sm:4px;--radius:7px;--radius-lg:11px;--radius-xl:16px;
}

*,*::before,*::after{box-sizing:border-box}

.stApp{
    background:var(--bg)!important;
    color:var(--t1);
    font-family:var(--font);
    font-size:var(--sz-body);
    line-height:1.6;
    -webkit-font-smoothing:antialiased
}

h1,h2,h3,h4{font-family:var(--font-head)!important;color:var(--t0)!important}
h1{font-size:var(--sz-xl)!important;font-weight:700!important}
h2{font-size:var(--sz-lg)!important;font-weight:700!important}
h3{font-size:var(--sz-body)!important;font-weight:600!important}
p,li{font-size:var(--sz-body)!important;color:var(--t0)!important;font-family:var(--font)!important}

code{
    background:var(--s1)!important;
    border:1px solid var(--b0)!important;
    border-radius:var(--radius-sm)!important;
    padding:2px 6px!important;
    font-family:var(--mono)!important;
    font-size:var(--sz-xs)!important;
    color:var(--blue)!important
}

/* ── Hide Streamlit chrome ── */
#MainMenu{visibility:hidden}
header[data-testid="stHeader"]{display:none!important}
div[data-testid="stToolbar"]{display:none!important}
div[data-testid="stDecoration"]{display:none!important}
footer{display:none!important}

.block-container{
    padding-top:0!important;
    padding-left:1.5rem!important;
    padding-right:1.5rem!important;
    max-width:100%!important
}

/* ── Inputs ── */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="select"]{
    background-color:var(--bg)!important;
    border:1px solid var(--b1)!important;
    border-radius:var(--radius)!important
}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="base-input"]:focus-within{
    border-color:var(--blue)!important;
    box-shadow:0 0 0 3px rgba(26,111,216,.10)!important
}
div[data-baseweb="input"] input{
    color:var(--t0)!important;
    -webkit-text-fill-color:var(--t0)!important;
    background-color:transparent!important;
    font-size:var(--sz-body)!important;
    padding:8px 12px!important;
    font-family:var(--font)!important
}
div[data-baseweb="input"]:has(input:disabled),
div[data-baseweb="base-input"]:has(input:disabled){
    background-color:transparent!important;border:none!important
}
div[data-baseweb="input"] input:disabled{
    color:var(--t0)!important;
    -webkit-text-fill-color:var(--t0)!important;
    cursor:default!important;
    padding-left:0!important
}

/* ── Buttons ── */
div[data-testid="stButton"] button{
    background-color:var(--s0)!important;
    color:var(--t0)!important;
    border:1px solid var(--b1)!important;
    border-radius:var(--radius)!important;
    padding:7px 14px!important;
    transition:all .15s ease!important;
    font-family:var(--font)!important;
    font-size:var(--sz-body)!important;
    font-weight:600!important
}
div[data-testid="stButton"] button:hover{
    border-color:var(--blue)!important;
    color:var(--t0)!important;
    background-color:var(--blue-g)!important;
    box-shadow:0 0 8px rgba(26,111,216,.12)!important
}
div[data-testid="stButton"] button:hover p,
div[data-testid="stButton"] button:hover span,
div[data-testid="stButton"] button:hover div{
    color:var(--t0)!important;
    -webkit-text-fill-color:var(--t0)!important
}
div[data-testid="stButton"] button[kind="primary"]{
    background:linear-gradient(135deg,var(--blue-dk) 0%,var(--blue) 100%)!important;
    color:#fff!important;
    border-color:transparent!important;
    font-weight:700!important;
    box-shadow:0 2px 10px rgba(26,111,216,.28)!important
}
div[data-testid="stButton"] button[kind="primary"]:hover{
    box-shadow:0 4px 18px rgba(26,111,216,.40)!important;
    transform:translateY(-1px);
    color:#fff!important
}
div[data-testid="stButton"] button:disabled{opacity:.35!important}

/* ── File uploader ── */
div[data-testid="stFileUploader"] button,
div[data-testid="stFileUploaderDropzone"] button{
    background-color:var(--s0)!important;
    color:var(--t0)!important;
    border:1px solid var(--b1)!important;
    border-radius:var(--radius)!important;
    font-family:var(--font)!important;
    font-size:var(--sz-body)!important;
    font-weight:600!important
}
div[data-testid="stFileUploader"] button:hover,
div[data-testid="stFileUploaderDropzone"] button:hover{
    border-color:var(--blue)!important;
    background-color:var(--blue-g)!important
}
div[data-testid="stFileUploader"]{
    background:var(--s0)!important;
    border:2px dashed var(--b1)!important;
    border-radius:var(--radius-lg)!important
}
div[data-testid="stFileUploader"]:hover{border-color:var(--blue)!important}

/* ── Hide the + Add files button ── */
button[data-testid="stBaseButton-borderlessIcon"][aria-label="Add files"],
[data-testid="stFileUploaderDropzone"] > div > button:last-of-type,
[data-testid="stFileUploaderDropzone"] button[title="Add files"]{
    display:none!important
}

/* ── Dialogs ── */
div[role="dialog"]{
    background-color:var(--bg)!important;
    border:1px solid var(--b0)!important;
    border-radius:var(--radius-xl)!important;
    box-shadow:var(--shadow-lg)!important
}
div[role="dialog"] *{color:var(--t1)!important}
div[role="dialog"] h1,div[role="dialog"] h2,div[role="dialog"] h3{color:var(--t0)!important}
div[role="dialog"] button{
    background:var(--s0)!important;
    border:1px solid var(--b1)!important;
    color:var(--t0)!important;
    border-radius:var(--radius)!important
}

/* ── Tabs ── */
div[data-baseweb="tab-list"]{
    background:var(--s0)!important;
    border-radius:var(--radius) var(--radius) 0 0!important;
    border-bottom:2px solid var(--b0)!important;
    padding:0 6px!important
}
div[data-baseweb="tab"]{
    color:var(--t3)!important;
    font-family:var(--mono)!important;
    font-weight:600!important;
    font-size:var(--sz-sm)!important;
    padding:11px 18px!important;
    border-bottom:2px solid transparent!important;
    transition:all .15s!important;
    margin-bottom:-2px!important
}
div[data-baseweb="tab"]:hover{color:var(--t1)!important}
div[data-baseweb="tab"][aria-selected="true"]{
    color:var(--blue)!important;
    border-bottom-color:var(--blue)!important;
    font-weight:700!important
}
div[data-baseweb="tab-panel"]{
    background:var(--bg)!important;
    border:1px solid var(--b0)!important;
    border-top:none!important;
    border-radius:0 0 var(--radius) var(--radius)!important;
    padding:18px!important
}

/* ── Selectbox / Dropdown ── */
div[data-baseweb="select"] > div{
    background-color:var(--bg)!important;
    border:1px solid var(--b1)!important;
    border-radius:var(--radius)!important;
    color:var(--t0)!important
}
div[data-baseweb="select"] > div:focus-within{
    border-color:var(--blue)!important;
    box-shadow:0 0 0 3px rgba(26,111,216,.10)!important
}
ul[data-baseweb="menu"]{
    background-color:var(--bg)!important;
    border:1px solid var(--b1)!important;
    border-radius:var(--radius)!important;
    box-shadow:var(--shadow)!important
}
li[role="option"]{
    background-color:var(--bg)!important;
    color:var(--t0)!important
}
li[role="option"]:hover,
li[role="option"][aria-selected="true"]{
    background-color:var(--blue-g)!important;
    color:var(--t0)!important
}
li[role="option"] span,
li[role="option"] div{
    color:var(--t0)!important;
    -webkit-text-fill-color:var(--t0)!important
}
div[data-baseweb="popover"] div,
div[data-baseweb="popover"] ul{
    background-color:var(--bg)!important;
    border-color:var(--b1)!important
}

/* ── DataFrames ── */
.stDataFrame thead th{
    background:var(--s0)!important;
    color:var(--blue)!important;
    font-family:var(--mono)!important;
    font-size:var(--sz-xs)!important;
    text-transform:uppercase!important;
    letter-spacing:.9px!important;
    border-color:var(--b0)!important;
    font-weight:600!important
}
.stDataFrame tbody td{
    color:var(--t1)!important;
    font-family:var(--font)!important;
    font-size:var(--sz-body)!important;
    border-color:var(--b0)!important
}

/* ── Tooltip ── */
div[role="tooltip"],
div[role="tooltip"] *,
div[role="tooltip"] p,
div[role="tooltip"] span,
div[role="tooltip"] div{
    background:var(--t0)!important;
    color:#ffffff!important;
    -webkit-text-fill-color:#ffffff!important;
    font-family:var(--font)!important;
    font-size:12px!important
}

/* ── Scrollbar ── */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--s0)}
::-webkit-scrollbar-thumb{background:var(--b1);border-radius:4px}
::-webkit-scrollbar-thumb:hover{background:var(--blue)}

/* ── Misc ── */
hr{border-color:var(--b0)!important;margin:16px 0!important}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"]{display:none!important}
div[data-testid="stForm"]{border:none!important;padding:0!important}
details{
    background:var(--s0)!important;
    border:1px solid var(--b0)!important;
    border-radius:var(--radius)!important;
    margin-bottom:8px!important
}
details summary{
    color:var(--t2)!important;
    font-family:var(--font)!important;
    font-weight:600!important;
    font-size:var(--sz-body)!important;
    padding:10px 14px!important
}
div[data-testid="stAlert"]{
    font-family:var(--font)!important;
    font-size:var(--sz-body)!important;
    border-radius:var(--radius)!important
}
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li{
    font-family:var(--font)!important;
    font-size:var(--sz-body)!important;
    color:var(--t0)!important
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] div{
    font-family:var(--font)!important;
    font-size:var(--sz-body)!important
}
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] label{
    font-family:var(--font)!important;
    font-size:var(--sz-sm)!important;
    font-weight:600!important;
    color:var(--t1)!important
}
div[data-testid="stCheckbox"] label{
    font-family:var(--font)!important;
    font-size:var(--sz-body)!important;
    color:var(--t0)!important
}

/* ── Sidebar ── */
[data-testid="stSidebar"]{
    background-color:var(--s0)!important;
    border-right:1px solid var(--b0)!important
}
[data-testid="stSidebarContent"]{background-color:var(--s0)!important}
[data-testid="stSidebar"] *{color:var(--t1)!important}
[data-testid="stSidebar"] button{
    background-color:var(--bg)!important;
    color:var(--t0)!important;
    border:1px solid var(--b1)!important;
    border-radius:var(--radius)!important
}
[data-testid="stSidebar"] button:hover{
    border-color:var(--blue)!important;
    background-color:var(--blue-g)!important
}

/* ── App-specific component classes ── */
.file-card{
    background:var(--bg);
    border:1px solid var(--b0);
    border-top:3px solid var(--blue);
    border-radius:var(--radius-xl);
    margin-bottom:18px;
    overflow:hidden;
    box-shadow:var(--shadow)
}
.file-card-header{
    background:var(--s0);
    border-bottom:1px solid var(--b0);
    padding:13px 20px;
    display:flex;align-items:center;justify-content:space-between
}
.file-card-title{
    font-size:var(--sz-body);font-weight:700;color:var(--t0);
    display:flex;align-items:center;gap:10px;font-family:var(--font-head)
}
.file-badge{
    font-family:var(--mono);font-size:10px;font-weight:600;
    padding:3px 10px;border-radius:20px;text-transform:uppercase;letter-spacing:1px
}
.badge-unique{
    background:var(--green-g);color:var(--green);
    border:1px solid rgba(10,158,106,.3)
}
.badge-duplicate{
    background:var(--yellow-g);color:var(--yellow);
    border:1px solid rgba(201,154,0,.3)
}
.file-card-body{
    display:grid;grid-template-columns:repeat(4,1fr);
    padding:18px 24px;gap:0;background:var(--bg)
}
.file-stat{display:flex;flex-direction:column;gap:5px}
.file-stat-lbl{
    font-size:var(--sz-xs);font-weight:800;color:var(--t0);
    text-transform:uppercase;letter-spacing:1.8px;font-family:var(--mono);margin-bottom:6px
}
.file-stat-val{font-size:var(--sz-lg);font-weight:700;color:var(--t0);font-family:var(--font);-webkit-text-fill-color:var(--t0)}
.file-stat-val.accent{color:var(--blue);font-weight:700}
.file-stat-val.mono-sm{
    font-size:var(--sz-xs);color:var(--t3);letter-spacing:.3px;
    word-break:break-all;font-weight:400;font-family:var(--mono)
}
.sheet-card{
    background:var(--bg);
    border:1px solid var(--b0);
    border-left:3px solid var(--blue);
    border-radius:var(--radius-lg);
    margin-bottom:16px;overflow:hidden;box-shadow:var(--shadow-sm)
}
.sheet-card-hdr{
    padding:12px 18px;display:flex;align-items:center;
    justify-content:space-between;border-bottom:1px solid var(--b0);background:var(--s0)
}
.sheet-card-name{
    font-size:var(--sz-body);font-weight:700;color:var(--t0);
    display:flex;align-items:center;gap:10px;font-family:var(--font-head)
}
.sheet-type-tag{
    font-family:var(--mono);font-size:10px;padding:3px 10px;border-radius:20px;
    text-transform:uppercase;letter-spacing:.8px;font-weight:600;
    background:var(--blue-g);border:1px solid rgba(26,111,216,.2);color:var(--blue)
}
.sheet-stats-grid{
    display:grid;grid-template-columns:repeat(6,1fr);
    padding:14px 18px;gap:12px;background:var(--bg)
}
.sh-stat{display:flex;flex-direction:column;gap:5px}
.sh-stat-lbl{
    font-size:var(--sz-xs);font-weight:800;color:var(--t0);
    text-transform:uppercase;letter-spacing:1.4px;font-family:var(--mono)
}
.sh-stat-val{font-size:var(--sz-body);font-weight:600;color:var(--t0);font-family:var(--font)}
.sh-stat-val.hi{color:var(--green);font-weight:700}
.sh-stat-val.mid{color:var(--yellow);font-weight:700}
.claim-card{
    background:var(--s0);border:1px solid var(--b0);
    border-radius:var(--radius);padding:12px 14px;margin-bottom:6px;
    cursor:pointer;transition:border-color .15s,box-shadow .15s,background .15s
}
.claim-card:hover{
    border-color:var(--blue);background:var(--blue-g);box-shadow:var(--shadow-sm)
}
.selected-card{
    border-left:3px solid var(--blue)!important;
    background:var(--blue-g)!important;
    box-shadow:0 0 12px rgba(26,111,216,.12)!important
}
.mandatory-asterisk{
    display:inline-block;font-size:var(--sz-body);color:var(--blue);
    font-weight:700;margin-left:3px;vertical-align:middle
}
.optional-badge{
    display:inline-block;background:var(--s1);border:1px solid var(--b0);
    border-radius:3px;font-size:var(--sz-xs);color:var(--t2);
    padding:0 5px;margin-left:4px;vertical-align:middle;font-family:var(--mono)
}
.custom-field-badge{
    display:inline-block;background:var(--purple-g);border:1px solid rgba(107,63,212,.3);
    border-radius:3px;font-size:10px;color:var(--purple);
    padding:0 5px;margin-left:4px;vertical-align:middle;font-family:var(--mono)
}
.llm-map-banner{
    background:var(--yellow-g);border:1px solid rgba(201,154,0,.25);
    border-left:3px solid var(--yellow);border-radius:var(--radius);
    padding:10px 14px;margin-bottom:12px
}
.navbar-title{
    font-size:15px;font-weight:700;color:var(--t0);
    font-family:var(--font-head);letter-spacing:-.2px;white-space:nowrap;line-height:1.2
}
.navbar-subtitle{
    font-size:10px;font-weight:400;color:var(--t3);
    font-family:var(--mono);letter-spacing:.4px;white-space:nowrap
}

/* ── Code blocks (st.code) ── */
div[data-testid="stCode"] pre,
div[data-testid="stCode"] code{
    background:var(--s0)!important;
    color:var(--t0)!important;
    border:1px solid var(--b0)!important;
    -webkit-text-fill-color:var(--t0)!important
}

    /* ── File uploader — force white background ── */
    div[data-testid="stFileUploader"],
    div[data-testid="stFileUploaderDropzone"],
    div[data-testid="stFileUploaderDropzoneInner"],
    section[data-testid="stFileUploadDropzone"],
    div[data-testid="stFileUploader"] > div,
    div[data-testid="stFileUploader"] > div > div,
    div[data-testid="stFileUploader"] section,
    div[data-testid="stFileUploader"] small {
        background-color: var(--s0) !important;
        background: var(--s0) !important;
        color: var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
    }
    div[data-testid="stFileUploader"] p,
    div[data-testid="stFileUploader"] span,
    div[data-testid="stFileUploader"] small,
    div[data-testid="stFileUploader"] label {
        color: var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
    }
    div[data-testid="stFileUploader"] svg {
        fill: var(--t0) !important;
        stroke: var(--t0) !important;
    }
    div[data-testid="stFileUploader"] {
        border: 2px dashed var(--b1) !important;
        border-radius: var(--radius-lg) !important;
    }
    div[data-testid="stFileUploader"]:hover {
        border-color: var(--blue) !important;
    }

    /* ── Expanders ── */
    div[data-testid="stExpander"] {
        background: var(--s0) !important;
        border: 1px solid var(--b0) !important;
        border-radius: var(--radius) !important;
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary *,
    div[data-testid="stExpander"] p {
        color: var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
    }

    /* ── Info / Warning / Error boxes ── */
    div[data-testid="stAlert"] {
        background: var(--s0) !important;
        border-color: var(--b0) !important;
    }
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] span {
        color: var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
    }

    /* ── st.code / st.json backgrounds ── */
    div[data-testid="stCode"],
    div[data-testid="stCode"] pre,
    div[data-testid="stCode"] code,
    .stCodeBlock,
    .stCodeBlock pre,
    .stCodeBlock code {
        background: var(--s0) !important;
        color: var(--t0) !important;
        border: 1px solid var(--b0) !important;
    }

    /* ── Spinner overlay ── */
    div[data-testid="stSpinner"] p,
    div[data-testid="stSpinner"] span {
        color: var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
    }

    /* ── Text area ── */
    textarea {
        background: var(--s0) !important;
        color: var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
        border: 1px solid var(--b1) !important;
        border-radius: var(--radius) !important;
    }

    /* ── Markdown containers ── */
    div[data-testid="stMarkdownContainer"] {
        color: var(--t0) !important;
    }

    /* ── Any remaining white-on-white text fixes ── */
    .stApp * {
        --text-color: var(--t0);
    }
    label, span:not([style*="color"]) {
        color: var(--t0) !important;
    }


    /* ── JSON / code block: green keys, blue values ── */
    div[data-testid="stCode"] pre,
    div[data-testid="stCode"] code,
    .stCodeBlock pre,
    .stCodeBlock code {
        background: #f6fef9 !important;
        border: 1px solid #b3e0c8 !important;
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    /* JSON string keys (before colon) */
    div[data-testid="stCode"] .hljs-attr,
    div[data-testid="stCode"] .token.property,
    .stCodeBlock .hljs-attr { color: #0a7a50 !important; font-weight: 600 !important; }
    /* JSON string values */
    div[data-testid="stCode"] .hljs-string,
    div[data-testid="stCode"] .token.string,
    .stCodeBlock .hljs-string { color: #1a6fd8 !important; }
    /* JSON numbers */
    div[data-testid="stCode"] .hljs-number,
    .stCodeBlock .hljs-number { color: #c99a00 !important; }
    /* JSON booleans/null */
    div[data-testid="stCode"] .hljs-literal,
    .stCodeBlock .hljs-literal { color: #d64040 !important; }

    /* ── Dialog popup: force light theme ── */
    div[role="dialog"] {
        background-color: #ffffff !important;
        border: 1px solid #d0d6e8 !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 32px rgba(30,50,100,.18) !important;
    }
    div[role="dialog"] * { color: #0f1117 !important; -webkit-text-fill-color: #0f1117 !important; }
    div[role="dialog"] h1,div[role="dialog"] h2,div[role="dialog"] h3 { color: #0f1117 !important; }
    div[role="dialog"] button {
        background: #f1f3f8 !important; border: 1px solid #d0d6e8 !important;
        color: #0f1117 !important; border-radius: 7px !important;
    }
    div[role="dialog"] button:hover {
        border-color: #1a6fd8 !important; background: rgba(26,111,216,0.07) !important;
    }
    /* Close X button in dialog */
    div[role="dialog"] button[aria-label="Close"],
    div[role="dialog"] button[data-testid="stBaseButton-header"] {
        background: transparent !important; border: none !important;
    }

    /* ── Uploaded file chip — make text readable ── */
    div[data-testid="stFileUploaderFile"],
    div[data-testid="stFileUploaderFileName"],
    div[data-testid="stUploadedFile"],
    div[data-testid="stUploadedFile"] *,
    div[data-testid="stFileUploaderFile"] span,
    div[data-testid="stFileUploaderFile"] small,
    span[data-testid="stFileUploaderFileName"] {
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
        background: #f1f3f8 !important;
    }
    /* The dark pill/chip that shows the filename */
    div[class*="uploadedFile"],
    div[class*="UploadedFile"],
    li[class*="uploadedFile"],
    li[class*="UploadedFile"] {
        background: #f1f3f8 !important;
        border: 1px solid #d0d6e8 !important;
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[class*="uploadedFile"] *,
    div[class*="UploadedFile"] *,
    li[class*="uploadedFile"] *,
    li[class*="UploadedFile"] * {
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }

    /* ══════════════════════════════════════════════════════════════
       UPLOADED FILE CHIP — nuclear override
    ══════════════════════════════════════════════════════════════ */
    [data-testid="stFileUploaderFile"],
    [data-testid="stFileUploaderDeleteBtn"],
    div[data-testid="stFileUploader"] [class*="File"],
    div[data-testid="stFileUploader"] [class*="file"],
    div[data-testid="stFileUploader"] li,
    div[data-testid="stFileUploader"] > div > div,
    div[data-testid="stFileUploaderDropzone"] + div,
    div[data-testid="stFileUploaderDropzone"] ~ div,
    section[data-testid="stFileUploadDropzone"] ~ div {
        background-color: #f1f3f8 !important;
        background:       #f1f3f8 !important;
        color:            #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
        border: 1px solid #d0d6e8 !important;
        border-radius: 6px !important;
    }
    div[data-testid="stFileUploader"] li *,
    div[data-testid="stFileUploader"] [class*="File"] *,
    div[data-testid="stFileUploader"] [class*="file"] *,
    div[data-testid="stFileUploader"] > div > div * {
        color:            #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[data-testid="stFileUploader"] svg,
    div[data-testid="stFileUploader"] [class*="File"] svg {
        fill:   #1a6fd8 !important;
        stroke: #1a6fd8 !important;
    }
    [class*="uploadedFileName"],
    [class*="UploadedFileName"],
    [class*="uploadedFileData"],
    [class*="UploadedFileData"],
    [class*="uploadedFile"],
    [class*="UploadedFile"] {
        background:       #f1f3f8 !important;
        color:            #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
        border: 1px solid #d0d6e8 !important;
    }
    [class*="uploadedFile"] *,
    [class*="UploadedFile"] * {
        color:            #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }

    /* ── Expander: full nuclear override ── */
    div[data-testid="stExpander"],
    div[data-testid="stExpander"] > div,
    div[data-testid="stExpander"] > div > div,
    div[data-testid="stExpander"] details,
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] > details,
    div[data-testid="stExpander"] > details > summary {
        background-color: var(--s0) !important;
        background:       var(--s0) !important;
        color:            var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
    }
    div[data-testid="stExpander"] summary:hover,
    div[data-testid="stExpander"] details summary:hover {
        background-color: var(--s1) !important;
    }
    div[data-testid="stExpander"] *,
    details * {
        color:            var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
    }
    [data-testid="stExpanderToggleIcon"] svg {
        fill:   var(--t0) !important;
        stroke: var(--t0) !important;
    }
    div[data-testid="stExpander"] > div[data-baseweb="block"],
    div[data-testid="stExpander"] > div > div[data-baseweb="block"] {
        background: var(--bg) !important;
    }
    div[data-testid="stExpanderDetails"] {
        background: var(--bg) !important;
        border-top: 1px solid var(--b0) !important;
    }
    div[data-testid="stExpanderDetails"] * {
        color: var(--t0) !important;
        -webkit-text-fill-color: var(--t0) !important;
    }

    /* ══════════════════════════════════════════════════════════════════
       FILE CHIP — maximum specificity override
    ═══════════════════════════════════════════════════════════════════ */
    div[data-testid="stFileUploader"] *:not(button):not(svg):not(path) {
        background-color: transparent !important;
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[data-testid="stFileUploader"] > div > div:not([data-testid]),
    div[data-testid="stFileUploader"] > div:last-child,
    div[data-testid="stFileUploaderDropzone"] ~ div,
    div[data-testid="stFileUploaderDropzone"] + div {
        background-color: #f1f3f8 !important;
        background: #f1f3f8 !important;
        border: 1px solid #d0d6e8 !important;
        border-radius: 8px !important;
        color: #0f1117 !important;
    }
    div[data-testid="stFileUploader"] li,
    div[data-testid="stFileUploader"] ul,
    div[data-testid="stFileUploader"] ol {
        background-color: #f1f3f8 !important;
        background: #f1f3f8 !important;
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
        list-style: none !important;
        border: 1px solid #d0d6e8 !important;
        border-radius: 6px !important;
        padding: 6px 10px !important;
        margin: 4px 0 !important;
    }
    div[data-testid="stFileUploader"] small,
    div[data-testid="stFileUploader"] span,
    div[data-testid="stFileUploader"] p {
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[data-testid="stFileUploader"] button[aria-label*="Delete"],
    div[data-testid="stFileUploader"] button[aria-label*="Remove"],
    div[data-testid="stFileUploaderDeleteBtn"],
    [data-testid="stFileUploaderDeleteBtn"] {
        background: #f1f3f8 !important;
        color: #d64040 !important;
        border: 1px solid #d0d6e8 !important;
    }
    div[data-testid="stFileUploader"] [style*="rgb(14"],
    div[data-testid="stFileUploader"] [style*="rgb(26"],
    div[data-testid="stFileUploader"] [style*="rgb(38"],
    div[data-testid="stFileUploader"] [style*="background-color: rgb(14"],
    div[data-testid="stFileUploader"] [style*="background-color: rgb(26"],
    div[data-testid="stFileUploader"] [style*="background-color: rgb(38"] {
        background-color: #f1f3f8 !important;
        background: #f1f3f8 !important;
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }

    /* ══════════════════════════════════════════════════════════════════
       DIALOG LIGHT THEME
    ═══════════════════════════════════════════════════════════════════ */
    div[role="dialog"] div[data-testid="stMarkdownContainer"] div[style*="background:#12"],
    div[role="dialog"] div[data-testid="stMarkdownContainer"] div[style*="background:#0d"],
    div[role="dialog"] div[data-testid="stMarkdownContainer"] div[style*="background:#17"],
    div[role="dialog"] div[data-testid="stMarkdownContainer"] div[style*="background:#1a"],
    div[role="dialog"] div[data-testid="stMarkdownContainer"] div[style*="background:#16"],
    div[role="dialog"] div[data-testid="stMarkdownContainer"] div[style*="background:#0a"],
    div[role="dialog"] div[data-testid="stMarkdownContainer"] div[style*="background:#0f"],
    div[role="dialog"] div[data-testid="stMarkdownContainer"] div[style*="background:#2a"],
    div[role="dialog"] div[data-testid="stMarkdownContainer"] table,
    div[role="dialog"] div[data-testid="stMarkdownContainer"] td,
    div[role="dialog"] div[data-testid="stMarkdownContainer"] th {
        background-color: #f8f9fc !important;
        background: #f8f9fc !important;
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
        border-color: #d0d6e8 !important;
    }
    div[role="dialog"] code {
        background: #f1f3f8 !important;
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
        border: 1px solid #d0d6e8 !important;
    }
    div[role="dialog"] span[style*="color:#e8e7ff"],
    div[role="dialog"] span[style*="color:#f0efff"],
    div[role="dialog"] span[style*="color:#a0a0c8"],
    div[role="dialog"] div[style*="color:#e8e7ff"],
    div[role="dialog"] div[style*="color:#f0efff"],
    div[role="dialog"] div[style*="color:#a0a0c8"],
    div[role="dialog"] div[style*="color:#c8d8ff"] {
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[role="dialog"] span[style*="color:#6b7280"],
    div[role="dialog"] div[style*="color:#6b7280"],
    div[role="dialog"] span[style*="color:#555;"] {
        color: #4a5578 !important;
        -webkit-text-fill-color: #4a5578 !important;
    }
    div[role="dialog"] td[style*="background:#12"],
    div[role="dialog"] td[style*="background:#1a"],
    div[role="dialog"] th[style*="background:#1a"] {
        background: #f1f3f8 !important;
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[role="dialog"] td[style*="background:#2a"] {
        background: #fffbeb !important;
        color: #0f1117 !important;
    }
    div[role="dialog"] div[data-testid="stAlert"] {
        background: #f8f9fc !important;
    }
    div[role="dialog"] div[data-testid="stAlert"] p,
    div[role="dialog"] div[data-testid="stAlert"] span {
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[role="dialog"] div[data-testid="stMarkdownContainer"] {
        color: #0f1117 !important;
    }
    div[role="dialog"] div[data-testid="stMarkdownContainer"] p,
    div[role="dialog"] div[data-testid="stMarkdownContainer"] span,
    div[role="dialog"] div[data-testid="stMarkdownContainer"] li {
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[role="dialog"] div[style*="background:#1a1a2e"],
    div[role="dialog"] div[style*="background:#16161e"] {
        background: #f8f9fc !important;
        color: #0f1117 !important;
    }
    div[role="dialog"] div[style*="background:#1a1a2e"] *,
    div[role="dialog"] div[style*="background:#16161e"] * {
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[role="dialog"] div[style*="background:#17172a"] {
        background: #f8f9fc !important;
        border-color: #d0d6e8 !important;
    }
    div[role="dialog"] div[style*="background:#17172a"] * {
        color: #0f1117 !important;
        -webkit-text-fill-color: #0f1117 !important;
    }
    div[role="dialog"] div[style*="background:#0d0d1a"] {
        background: #f8f9fc !important;
    }
    div[role="dialog"] div[style*="background:#2a1218"] {
        background: #fff0f0 !important;
    }
    div[role="dialog"] div[style*="background:#0a2a1a"] {
        background: #f0fdf6 !important;
    }
    div[role="dialog"] div[style*="background:#12121c"] {
        background: #f1f3f8 !important;
    }
    div[role="dialog"] hr {
        border-color: #d0d6e8 !important;
    }

    /* ══════════════════════════════════════════════════════════════════
       ICON BUTTONS (eye / edit) — zoom-safe fixed size
       Prevents 👁 and ✏ buttons from becoming disproportionate on zoom
    ═══════════════════════════════════════════════════════════════════ */
    .icon-btn-wrap {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 38px !important;
        min-width: 38px !important;
        max-width: 38px !important;
    }
    .icon-btn-wrap > div[data-testid="stButton"] {
        width: 38px !important;
        min-width: 38px !important;
        max-width: 38px !important;
    }
    .icon-btn-wrap > div[data-testid="stButton"] > button {
        width: 38px !important;
        min-width: 38px !important;
        max-width: 38px !important;
        padding: 5px 0 !important;
        font-size: 15px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

</style>
"""