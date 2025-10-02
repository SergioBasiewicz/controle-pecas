import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import uuid
import time
import os
import json

# Conexão com Google Sheets - Apenas variáveis de ambiente para produção
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]

# Carregar credenciais apenas das variáveis de ambiente
creds_json = os.environ.get('GOOGLE_CREDENTIALS')
if creds_json:
    try:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        st.sidebar.success("✅ Conectado ao Google Sheets")
    except Exception as e:
        st.error(f"Erro nas credenciais: {e}")
        st.stop()
else:
    st.error("❌ Credenciais do Google Sheets não encontradas")
    st.stop()

client = gspread.authorize(creds)

# Abrir planilha usando ID fornecido
spreadsheet_id = "1rRYEj-Kvtyqqu8YQSiw-v2dgMf5a_kGYV7aQa1ue1JI"
sheet = client.open_by_key(spreadsheet_id).worksheet("Pedidos")

def get_pedidos():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def adicionar_pedido(solicitante, peca, tecnico, observacoes):
    linhas = sheet.get_all_values()
    ids_existentes = [linha[0] for linha in linhas]
    
    while True:
        novo_id = str(uuid.uuid4())[:8]
        if novo_id not in ids_existentes:
            break
    
    data = datetime.now().strftime("%d/%m/%Y")
    status = "Pendente"
    sheet.append_row([novo_id, data, solicitante, peca, tecnico, status, observacoes])
    st.success(f"Pedido {novo_id} adicionado!")

def atualizar_status(pedido_id, novo_status):
    pedidos = sheet.get_all_values()
    for i, linha in enumerate(pedidos):
        if linha[0] == str(pedido_id):
            sheet.update_cell(i+1, 6, novo_status)
            st.success(f"Status do pedido {pedido_id} atualizado para {novo_status}")
            return
    st.error("Pedido não encontrado.")

# ══════════════════════════════════════════════════════════════════════════════
# ⚠️ ALTERE A SENHA ABAIXO - TROQUE "admin123" PELA SUA SENHA DESEJADA ⚠️
SENHA_AUTORIZACAO = "admin123"  # ⬅️ MUDE ESTA SENHA!
# ══════════════════════════════════════════════════════════════════════════════

# Tempo para mensagem sumir (em segundos)
TEMPO_MENSAGEM = 5

# Inicializar session_state
if 'autorizado' not in st.session_state:
    st.session_state.autorizado = False
if 'mostrar_mensagem' not in st.session_state:
    st.session_state.mostrar_mensagem = False
if 'tempo_mensagem' not in st.session_state:
    st.session_state.tempo_mensagem = 0

st.title("Controle de Pedidos de Peças Usadas")

menu = st.sidebar.selectbox("Menu", ["Adicionar Pedido", "Visualizar Pedidos", "Atualizar Status"])

if menu == "Adicionar Pedido":
    st.header("Adicionar Pedido")
    solicitante = st.text_input("Solicitante")
    peca = st.text_input("Peça")
    tecnico = st.text_input("Técnico Responsável")
    observacoes = st.text_area("Observações")
    if st.button("Adicionar"):
        adicionar_pedido(solicitante, peca, tecnico, observacoes)

elif menu == "Visualizar Pedidos":
    st.header("Lista de Pedidos")
    df = get_pedidos()
    if not df.empty:
        st.dataframe(df)
        
        # Mostrar estatísticas rápidas
        st.subheader("📊 Estatísticas")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Pedidos", len(df))
        
        with col2:
            pendentes = len(df[df['Status:'] == 'Pendente'])
            st.metric("Pendentes", pendentes)
        
        with col3:
            entregues = len(df[df['Status:'] == 'Entregue'])
            st.metric("Entregues", entregues)
            
        # Mostrar também solicitados
        st.write("---")
        col4, col5, col6 = st.columns(3)
        with col4:
            solicitados = len(df[df['Status:'] == 'Solicitado'])
            st.metric("Solicitados", solicitados)
        with col5:
            # Percentual de entregues
            if len(df) > 0:
                percent_entregue = (entregues / len(df)) * 100
                st.metric("Taxa de Entrega", f"{percent_entregue:.1f}%")
            else:
                st.metric("Taxa de Entrega", "0%")
                
    else:
        st.info("Nenhum pedido cadastrado.")


elif menu == "Atualizar Status":
    st.header("Atualizar Status do Pedido")
    
    # Se não está autorizado, pede a senha
    if not st.session_state.autorizado:
        senha = st.text_input("Digite a senha de autorização", type="password")
        
        if st.button("Validar Senha"):
            if senha == SENHA_AUTORIZACAO:
                st.session_state.autorizado = True
                st.session_state.mostrar_mensagem = True
                st.session_state.tempo_mensagem = time.time()
                st.rerun()
            else:
                st.error("❌ Senha incorreta. Tente novamente.")
    
    # Se está autorizado, mostra os campos de atualização E a lista de IDs
    else:
        # Função para carregar os dados dos pedidos
        def carregar_pedidos():
            try:
                dados_brutos = sheet.get_all_values()
                return dados_brutos
            except Exception as e:
                st.sidebar.error(f"Erro ao carregar pedidos: {e}")
                return []
        
        # PRIMEIRO mostramos os controles de administrador no TOPO da sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔧 Controles Admin")
        
        # Botão para sair no TOPO da sidebar
        if st.sidebar.button("🚪 Sair do Modo Admin"):
            st.session_state.autorizado = False
            st.session_state.mostrar_mensagem = False
            st.rerun()
        
        # DEPOIS mostramos a lista de pedidos
        st.sidebar.subheader("📋 Todos os Pedidos")
        
        dados_brutos = carregar_pedidos()
        
        if len(dados_brutos) > 1:
            cabecalho = dados_brutos[0]
            dados = dados_brutos[1:]
            
            # Container para os pedidos com scroll
            with st.sidebar.container():
                for i, linha in enumerate(dados):
                    if linha and linha[0]:  # Se a linha não está vazia e tem ID
                        # Criar um card para cada pedido
                        with st.expander(f"📦 Pedido {linha[0]} - {linha[5]}", expanded=False):
                            # Definir cor baseada no status
                            status = linha[5] if len(linha) > 5 else "N/A"
                            status_color = {
                                "Pendente": "🔴",
                                "Solicitado": "🟡", 
                                "Entregue": "🟢"
                            }.get(status, "⚪")
                            
                            # Mostrar informações formatadas
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                st.write(f"**{cabecalho[0]}**")
                                st.write(f"**{cabecalho[1]}**")
                                st.write(f"**{cabecalho[2]}**")
                                st.write(f"**{cabecalho[3]}**")
                            
                            with col2:
                                st.write(linha[0])
                                st.write(linha[1])
                                st.write(linha[2])
                                st.write(linha[3])
                            
                            st.write(f"**{cabecalho[4]}:** {linha[4]}")
                            st.write(f"**{cabecalho[5]}:** {status_color} {linha[5]}")
                            
                            if len(linha) > 6 and linha[6]:
                                st.write(f"**{cabecalho[6]}:**")
                                st.info(linha[6])
                
                st.sidebar.caption(f"📊 Total de pedidos: {len(dados)}")
        else:
            st.sidebar.info("🎯 Nenhum pedido cadastrado")
        
        # Cria um placeholder para a mensagem
        mensagem_placeholder = st.empty()
        
        # Mostra e controla a mensagem
        if st.session_state.mostrar_mensagem:
            tempo_atual = time.time()
            tempo_decorrido = tempo_atual - st.session_state.tempo_mensagem
            tempo_restante = max(0, TEMPO_MENSAGEM - tempo_decorrido)
            
            if tempo_restante > 0:
                mensagem_placeholder.success(f"✅ Acesso autorizado!")
            else:
                mensagem_placeholder.empty()
                st.session_state.mostrar_mensagem = False
        
        # Campos de atualização no MAIN (não na sidebar)
        st.subheader("Atualizar Pedido")
        
        pedido_id = st.text_input("ID do Pedido")
        novo_status = st.selectbox("Novo Status", ["Pendente", "Solicitado", "Entregue"])
        
        if st.button("Atualizar Status"):
            if pedido_id:
                atualizar_status(pedido_id, novo_status)
                st.success("Status atualizado! Atualizando lista...")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Por favor, informe o ID do pedido")