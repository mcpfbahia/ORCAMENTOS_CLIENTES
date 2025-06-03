import streamlit as st
import pandas as pd
from PIL import Image
from fpdf import FPDF
import tempfile
import os
from urllib.parse import quote
import re
import unicodedata

# === FUNÇÕES AUXILIARES ===
def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_para_pdf(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return ''.join(c for c in texto if 32 <= ord(c) <= 126 or c in '\n\r\t')

def calcular_valor_com_desconto(valor, desconto):
    return valor * (1 - desconto / 100)

def calcular_frete(peso):
    return (peso / 1000) * 1150

def calcular_chave_na_mao(valor, descricao_kit):
    descricao = descricao_kit.upper()
    if "A-FRAME" in descricao:
        return valor * 2.00
    else:
        return valor * 2.15

# === INTERFACE STREAMLIT ===
st.set_page_config(page_title="🏠 MCPF - BAHIA SIMULADOR DE VENDAS", layout="centered")

# ✅ Banner
if os.path.exists("banner.png"):
    banner = Image.open("banner.png")
    st.image(banner, use_container_width=True)
else:
    st.title("Minha Casa Pré-Fabricada - Bahia")

st.caption("Consulte valores, descontos, frete e link do kit em segundos!")

# 📌 Carrega planilha
df = pd.read_excel("precos.xlsx")

# ✅ Campo de busca
busca_modelo = st.text_input("🔍 Digite parte do nome do kit:", placeholder="Ex: pousada, A-frame, 32m²")

if not busca_modelo.strip():
    st.info("Digite ao menos parte do nome do kit para começar.")
    st.stop()

opcoes_filtradas = df[df['DESCRICAO'].str.contains(busca_modelo, case=False, na=False)].head(10)

if not opcoes_filtradas.empty:
    kit_selecionado = st.selectbox("Selecione um kit:", opcoes_filtradas['DESCRICAO'].tolist(), key="kit_select")
    st.success(f"📦 Kit selecionado: {kit_selecionado}")
else:
    st.warning("Nenhum modelo encontrado com esse termo.")
    st.stop()

# ✅ Nome do cliente
nome_cliente = st.text_input("Nome do cliente (opcional):")

# Controle de troca
if 'kit_anterior' not in st.session_state:
    st.session_state.kit_anterior = kit_selecionado
if kit_selecionado != st.session_state.kit_anterior:
    st.session_state.kit_anterior = kit_selecionado
    st.rerun()

kit = df[df['DESCRICAO'] == kit_selecionado].iloc[0]
valor_kit = float(kit.get('A VISTA', 0))
peso_und = float(kit.get('PESO UND', 0))
link_kit = kit.get('LINK_KIT', '')
area_total = float(kit.get('AREA', 0))

# === RESULTADO
with st.expander("🔍 Resultado da Simulação", expanded=True):
    st.write(f"👤 **Cliente:** {nome_cliente if nome_cliente else 'Não informado'}")
    st.write(f"📦 **Modelo Selecionado:** {kit_selecionado}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**💰 Valor à Vista**")
        st.write(formatar_moeda(valor_kit))
        tipo_pagamento = st.radio("Forma de Pagamento:", ["À Vista", "Cartão de Crédito"])
        max_desconto = 12 if tipo_pagamento == "À Vista" else 5
        desconto = st.slider(f"Desconto (%) - máx. {max_desconto}%", 0, max_desconto, 0)
        valor_com_desconto = calcular_valor_com_desconto(valor_kit, desconto)
        st.markdown("**💲 Com Desconto**")
        st.write(formatar_moeda(valor_com_desconto))

    with col2:
        valor_chave_na_mao = calcular_chave_na_mao(valor_kit, kit_selecionado)
        valor_frete = calcular_frete(peso_und)
        valor_total_com_frete = valor_com_desconto + valor_frete

        st.markdown("**📐 Estimativa Casa Pronta**")
        st.write(formatar_moeda(valor_chave_na_mao))

        st.markdown("**🚚 Frete Estimado**")
        st.write(f"{formatar_moeda(valor_frete)} (pago direto à transportadora)")

        st.markdown("**💵 Valor Total com Frete**")
        st.write(f"{formatar_moeda(valor_com_desconto)} + {formatar_moeda(valor_frete)} = **{formatar_moeda(valor_total_com_frete)}**")

        if area_total > 0:
            dias_estimados = round(area_total / 12)
            st.write(f"🕒 Estimativa de montagem: {dias_estimados} dias úteis")

# ✅ Link online
if link_kit and str(link_kit).lower() != 'nan':
    st.markdown(f"[🔗 VER MODELO ONLINE]({link_kit})", unsafe_allow_html=True)
else:
    st.markdown(f"<span style='color: red;'>🔗 Link do modelo não disponível.</span>", unsafe_allow_html=True)

# ✅ Observação montagem
observacao = (
    "📌 OBS: O kit acompanha manual detalhado de montagem e suporte técnico da nossa equipe de engenheiros. "
    "Você pode contratar um carpinteiro local ou utilizar um de nossos parceiros. Essa opção costuma ser mais econômica, "
    "pois evita custos com deslocamentos técnicos e visitas à obra.\n\n"
    "Mas, se preferir mais comodidade, oferecemos também a opção CHAVE NA MÃO — com a casa entregue pronta no local. "
    "Consulte as condições dessa modalidade."
)

# ✅ Mensagem WhatsApp
mensagem = (
    f"👤 Cliente: {nome_cliente if nome_cliente else 'Não informado'}\n"
    f"📦 Kit: {kit_selecionado}\n\n"
    f"💰 Valor à vista: {formatar_moeda(valor_kit)}\n"
    f"💲 Valor com {desconto}% de desconto ({tipo_pagamento}): {formatar_moeda(valor_com_desconto)}\n"
    f"🚚 Frete estimado: {formatar_moeda(valor_frete)} (pago direto à transportadora)\n"
    f"💵 Total com Frete: {formatar_moeda(valor_total_com_frete)}\n"
    f"🏠 Estimativa casa pronta: {formatar_moeda(valor_chave_na_mao)}\n\n"
    f"{observacao}\n\n"
    f"🔗 Link do modelo: {link_kit if link_kit else 'Não disponível'}"
)

link_whatsapp = f"https://api.whatsapp.com/send?text={quote(mensagem)}"
st.markdown(f"[📲 Enviar via WhatsApp]({link_whatsapp})", unsafe_allow_html=True)

# ✅ PDF
if st.button("📄 Baixar Proposta em PDF"):
    pdf = FPDF()
    pdf.add_page()

    if os.path.exists("banner.png"):
        try:
            pdf.image("banner.png", x=10, y=8, w=180)
            pdf.ln(50)
        except:
            pass

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Proposta Comercial - MCPF Bahia", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Cliente: {limpar_para_pdf(nome_cliente)}", ln=True)
    pdf.cell(0, 10, f"Kit: {limpar_para_pdf(kit_selecionado)}", ln=True)
    pdf.cell(0, 10, f"Valor a vista: {formatar_moeda(valor_kit)}", ln=True)
    pdf.cell(0, 10, f"Desc. aplicado: {desconto}%", ln=True)
    pdf.cell(0, 10, f"Valor com desconto: {formatar_moeda(valor_com_desconto)}", ln=True)
    pdf.cell(0, 10, f"Frete estimado: {formatar_moeda(valor_frete)}", ln=True)
    pdf.cell(0, 10, f"Total com frete: {formatar_moeda(valor_total_com_frete)}", ln=True)
    pdf.cell(0, 10, f"Estimativa casa pronta: {formatar_moeda(valor_chave_na_mao)}", ln=True)
    if area_total > 0:
        pdf.cell(0, 10, f"Montagem estimada: {dias_estimados} dias úteis", ln=True)
    pdf.ln(5)

    # Link
    pdf.set_text_color(0, 0, 255)
    pdf.set_font("Arial", "U", 12)
    if link_kit:
        pdf.write(5, limpar_para_pdf("Clique aqui para ver o modelo online"), str(link_kit))
    else:
        pdf.set_text_color(255, 0, 0)
        pdf.write(5, "Link do modelo não disponível.")
    pdf.ln(10)

    # Observação
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, limpar_para_pdf(observacao))

    nome_base = re.sub(r'[^a-zA-Z0-9_]', '', limpar_para_pdf(nome_cliente.strip().replace(" ", "_"))) if nome_cliente else "mcpf"
    nome_pdf = f"proposta_{nome_base}.pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        st.download_button(
            label="📥 Clique para baixar a proposta",
            data=open(tmp.name, "rb"),
            file_name=nome_pdf,
            mime="application/pdf"
        )
    st.success("✅ Proposta gerada e pronta para download!")
