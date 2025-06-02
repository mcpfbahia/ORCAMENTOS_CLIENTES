import streamlit as st
import pandas as pd
from PIL import Image
from fpdf import FPDF
import tempfile
import os
from urllib.parse import quote

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_texto(texto):
    return texto.encode("latin-1", "ignore").decode("latin-1")

# ✅ Banner
banner = Image.open("banner.png")
st.image(banner, use_container_width=True)

st.caption("Consulte valores, descontos, frete e link do kit em segundos!")

# 📌 Carrega planilha
df = pd.read_excel("precos.xlsx")

# ✅ Campo de busca
busca_modelo = st.text_input("🔍 Digite parte do nome do kit:", placeholder="Ex: pousada, A-frame, 32m²")

if not busca_modelo.strip():
    st.info("Digite ao menos parte do nome do kit para começar.")
    st.stop()

opcoes_filtradas = df[df['DESCRICAO'].str.contains(busca_modelo, case=False, na=False)]

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

# Dados do kit
kit = df[df['DESCRICAO'] == kit_selecionado].iloc[0]
valor_kit = kit['A VISTA']
peso_und = kit['PESO UND']
link_kit = kit['LINK_KIT']
area_total = kit.get('AREA', 0)

# ✅ Resultado
with st.expander("🔍 Resultado da Simulação", expanded=True):

    # Mostrar nome e kit
    st.write(f"👤 **Cliente:** {nome_cliente if nome_cliente else 'Não informado'}")
    st.write(f"📦 **Modelo Selecionado:** {kit_selecionado}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**💰 Valor à Vista**")
        st.write(formatar_moeda(valor_kit))

        tipo_pagamento = st.radio("Forma de Pagamento:", ["À Vista", "Cartão de Crédito"])
        max_desconto = 12 if tipo_pagamento == "À Vista" else 5
        desconto = st.slider(f"Desconto (%) - máx. {max_desconto}%", 0, max_desconto, 0)
        valor_com_desconto = valor_kit * (1 - desconto / 100)

        st.markdown("**💲 Com Desconto**")
        st.write(formatar_moeda(valor_com_desconto))

    with col2:
        if "A-FRAME" in kit_selecionado.upper():
            valor_chave_na_mao = valor_kit * 2.0
        else:
            valor_chave_na_mao = valor_kit * 2.15

        valor_frete = (peso_und / 1000) * 1150

        st.markdown("**📐 Estimativa Média de Casa Pronta**")
        st.write(formatar_moeda(valor_chave_na_mao))

        st.markdown("**🚚 Frete Estimado**")
        st.write(f"{formatar_moeda(valor_frete)} (pago direto à transportadora)")

        valor_total_com_frete = valor_com_desconto + valor_frete
        st.markdown("**💵 Valor Total com Frete**")
        st.write(f"{formatar_moeda(valor_com_desconto)} + {formatar_moeda(valor_frete)} = **{formatar_moeda(valor_total_com_frete)}**")

        if area_total and area_total > 0:
            dias_estimados = round(area_total / 12)
            st.write(f"🕒 Estimativa montagem: {dias_estimados} dias")

# ✅ Link clicável para o modelo
st.markdown(f"[🔗 VER MODELO ONLINE]({link_kit})", unsafe_allow_html=True)

# ✅ Mensagem WhatsApp com link incluído
mensagem = (
    f"👤 Cliente: {nome_cliente if nome_cliente else 'Não informado'}\n"
    f"📦 Kit: {kit_selecionado}\n\n"
    f"💰 Valor à vista: {formatar_moeda(valor_kit)}\n"
    f"💲 Valor com {desconto}% de desconto ({tipo_pagamento}): {formatar_moeda(valor_com_desconto)}\n"
    f"🚚 Frete estimado: {formatar_moeda(valor_frete)} (pago direto à transportadora)\n"
    f"💵 Total com Frete: {formatar_moeda(valor_total_com_frete)}\n"
    f"🏠 Estimativa casa pronta: {formatar_moeda(valor_chave_na_mao)}\n\n"
    f"🔗 Link do modelo: {link_kit}"
)

mensagem_codificada = quote(mensagem)
link_whatsapp = f"https://wa.me/?text={mensagem_codificada}"
st.markdown(f"[📲 Enviar via WhatsApp]({link_whatsapp})", unsafe_allow_html=True)

# ✅ PDF com o total final
if st.button("📄 Baixar Proposta em PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    try:
        pdf.image("banner.png", x=10, y=8, w=180)
        pdf.ln(50)
    except:
        pdf.cell(200, 10, txt="Proposta - MCPF BAHIA", ln=True, align='C')
        pdf.ln(10)

    # ✅ Escreve a mensagem formatada (com cliente, kit, valores e link incluído)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 10, txt=limpar_texto(mensagem))

    # ✅ Adiciona o link clicável do modelo
    pdf.ln(5)
    pdf.set_text_color(0, 0, 255)
    pdf.set_font("Arial", "U", 12)
    pdf.write(5, limpar_texto("🔗 Clique aqui para ver o modelo online"), link_kit)
    pdf.ln(10)

    # ✅ Define nome do arquivo com base no nome do cliente (limpo)
    import re
    nome_base = re.sub(r'[^a-zA-Z0-9_]', '', limpar_texto(nome_cliente.strip().replace(" ", "_"))) if nome_cliente else "mcpf"
    nome_pdf = f"proposta_{nome_base}.pdf"

    # ✅ Gera arquivo PDF temporário e botão de download
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        st.download_button(
            label="📥 Clique para baixar a proposta",
            data=open(tmp.name, "rb"),
            file_name=nome_pdf,
            mime="application/pdf"
        )
