import boto3
import streamlit as st
import os
import uuid
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Any
import time
import sqlite3

from langchain_community.embeddings import BedrockEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain.llms.bedrock import Bedrock
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

# Konfigurasi AWS
AWS_REGION = "us-east-1"
BUCKET_NAME = os.getenv("BUCKET_NAME", "rifai-ai-bucket")

# Database untuk menyimpan chat history
DB_PATH = "financial_ai_chats.db"


class ChatManager:
    """Mengelola chat sessions dan persistensi dengan S3 sync"""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.sync_from_s3()
        self.init_database()

    def sync_from_s3(self):
        """Download database dari S3 jika ada"""
        try:
            self.s3_client.download_file(BUCKET_NAME, CHAT_DB_S3_KEY, DB_PATH)
            print("✅ Database downloaded from S3")
        except Exception as e:
            print(f"ℹ️ No existing database in S3 or error: {e}")

    def sync_to_s3(self):
        """Upload database ke S3"""
        try:
            self.s3_client.upload_file(DB_PATH, BUCKET_NAME, CHAT_DB_S3_KEY)
            print("✅ Database synced to S3")
            return True
        except Exception as e:
            print(f"❌ Failed to sync to S3: {e}")
            return False

    def init_database(self):
        """Inisialisasi database SQLite"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS chat_sessions
                       (
                           id
                           TEXT
                           PRIMARY
                           KEY,
                           title
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           updated_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           user_id
                           TEXT
                           DEFAULT
                           'default'
                       )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS chat_messages
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           session_id
                           TEXT
                           NOT
                           NULL,
                           role
                           TEXT
                           NOT
                           NULL,
                           content
                           TEXT
                           NOT
                           NULL,
                           timestamp
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           session_id
                       ) REFERENCES chat_sessions
                       (
                           id
                       )
                           )
                       ''')

        # Index untuk performa
        cursor.execute('''
                       CREATE INDEX IF NOT EXISTS idx_session_messages
                           ON chat_messages(session_id, timestamp)
                       ''')

        conn.commit()
        conn.close()

    def create_new_session(self, title: str = None, user_id: str = "default") -> str:
        """Membuat session chat baru"""
        session_id = str(uuid.uuid4())
        if not title:
            title = f"Chat {datetime.now().strftime('%d/%m %H:%M')}"

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_sessions (id, title, user_id) VALUES (?, ?, ?)",
            (session_id, title, user_id)
        )
        conn.commit()
        conn.close()

        # Sync ke S3 setelah perubahan
        self.sync_to_s3()
        return session_id

    def get_all_sessions(self, user_id: str = "default") -> List[Dict]:
        """Mendapatkan semua chat sessions untuk user tertentu"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'title': row[1],
                'created_at': row[2],
                'updated_at': row[3]
            })
        conn.close()
        return sessions

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Mendapatkan pesan dalam session"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, timestamp FROM chat_messages WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'role': row[0],
                'content': row[1],
                'timestamp': row[2]
            })
        conn.close()
        return messages

    def add_message(self, session_id: str, role: str, content: str):
        """Menambah pesan ke session"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        # Update session timestamp
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
        conn.commit()
        conn.close()

        # Sync ke S3 setelah setiap pesan (optional, bisa dibatasi)
        if len(content) > 100:  # Sync hanya untuk pesan panjang
            self.sync_to_s3()

    def delete_session(self, session_id: str):
        """Menghapus session dan semua pesannya"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()

        # Sync ke S3 setelah delete
        self.sync_to_s3()

    def update_session_title(self, session_id: str, title: str):
        """Update judul session"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, session_id)
        )
        conn.commit()
        conn.close()

        # Sync ke S3 setelah update
        self.sync_to_s3()

    def force_sync(self):
        """Paksa sync database ke S3"""
        return self.sync_to_s3()

    def export_chat_history(self, session_id: str = None) -> Dict:
        """Export chat history untuk backup"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if session_id:
            # Export session tertentu
            cursor.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
            sessions = cursor.fetchall()
            cursor.execute("SELECT * FROM chat_messages WHERE session_id = ?", (session_id,))
            messages = cursor.fetchall()
        else:
            # Export semua
            cursor.execute("SELECT * FROM chat_sessions")
            sessions = cursor.fetchall()
            cursor.execute("SELECT * FROM chat_messages")
            messages = cursor.fetchall()

        conn.close()

        return {
            'sessions': sessions,
            'messages': messages,
            'exported_at': datetime.now().isoformat()
        }

    def get_chat_statistics(self, user_id: str = "default") -> Dict:
        """Statistik penggunaan chat"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Total sessions
        cursor.execute("SELECT COUNT(*) FROM chat_sessions WHERE user_id = ?", (user_id,))
        total_sessions = cursor.fetchone()[0]

        # Total messages
        cursor.execute("""
                       SELECT COUNT(*)
                       FROM chat_messages cm
                                JOIN chat_sessions cs ON cm.session_id = cs.id
                       WHERE cs.user_id = ?
                       """, (user_id,))
        total_messages = cursor.fetchone()[0]

        # Messages by role
        cursor.execute("""
                       SELECT role, COUNT(*)
                       FROM chat_messages cm
                                JOIN chat_sessions cs ON cm.session_id = cs.id
                       WHERE cs.user_id = ?
                       GROUP BY role
                       """, (user_id,))
        messages_by_role = dict(cursor.fetchall())

        conn.close()

        return {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'messages_by_role': messages_by_role,
            'user_id': user_id
        }


# Initialize AWS clients
@st.cache_resource
def init_aws_clients():
    return {
        's3': boto3.client("s3"),
        'bedrock': boto3.client(service_name="bedrock-runtime", region_name=AWS_REGION)
    }


@st.cache_resource
def init_embeddings():
    clients = init_aws_clients()
    return BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v1",
        client=clients['bedrock']
    )


@st.cache_resource
def init_llm():
    clients = init_aws_clients()
    return Bedrock(
        model_id="anthropic.claude-v2:1",
        client=clients['bedrock'],
        model_kwargs={'max_tokens_to_sample': 1024}
    )


class FinancialAI:
    def __init__(self):
        self.clients = init_aws_clients()
        self.embeddings = init_embeddings()
        self.llm = init_llm()
        self.vectorstore = None

    def get_unique_id(self):
        return str(uuid.uuid4())

    def upload_to_s3(self, file_path: str, s3_key: str) -> bool:
        try:
            self.clients['s3'].upload_file(file_path, BUCKET_NAME, s3_key)
            return True
        except Exception as e:
            st.error(f"❌ Gagal upload ke S3: {e}")
            return False

    def download_from_s3(self, s3_key: str, local_path: str) -> bool:
        try:
            self.clients['s3'].download_file(BUCKET_NAME, s3_key, local_path)
            return True
        except Exception as e:
            st.error(f"❌ Gagal download dari S3: {e}")
            return False

    def process_financial_document(self, file_path: str, file_type: str) -> List[Document]:
        """Memproses dokumen keuangan dengan optimasi khusus"""
        documents = []

        if file_type == "pdf":
            try:
                loader = PyPDFLoader(file_path)
                documents = loader.load_and_split()
            except Exception as e:
                st.error(f"❌ Gagal membaca PDF: {e}")
                return []

        elif file_type in ["csv", "xlsx"]:
            try:
                if file_type == "csv":
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)

                financial_summary = self.create_financial_summary(df)
                full_text = df.to_string(index=False)
                documents.append(Document(
                    page_content=f"RINGKASAN KEUANGAN:\n{financial_summary}\n\nDATA LENGKAP:\n{full_text}",
                    metadata={"source": file_path, "type": "financial_data"}
                ))

            except Exception as e:
                st.error(f"❌ Gagal membaca file {file_type}: {e}")
                return []

        return documents

    def create_financial_summary(self, df: pd.DataFrame) -> str:
        """Membuat ringkasan otomatis dari data keuangan"""
        summary = []
        financial_columns = []

        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in
                   ['revenue', 'income', 'profit', 'expense', 'cost', 'sales', 'pendapatan', 'laba', 'biaya',
                    'penjualan']):
                financial_columns.append(col)

        summary.append(f"Total baris data: {len(df)}")
        summary.append(f"Kolom yang terdeteksi: {', '.join(df.columns)}")

        if financial_columns:
            summary.append(f"Kolom keuangan utama: {', '.join(financial_columns)}")
            for col in financial_columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    total = df[col].sum()
                    avg = df[col].mean()
                    summary.append(f"{col}: Total = {total:,.2f}, Rata-rata = {avg:,.2f}")

        return "\n".join(summary)

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Memecah dokumen menjadi chunk yang optimal"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=300,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

        split_docs = text_splitter.split_documents(documents)
        filtered_docs = []
        for doc in split_docs:
            content_length = len(doc.page_content)
            if 50 <= content_length <= 4000:
                filtered_docs.append(doc)

        return filtered_docs

    def create_vector_store(self, documents: List[Document]) -> bool:
        """Membuat dan menyimpan vector store"""
        try:
            vectorstore = FAISS.from_documents(documents, self.embeddings)
            temp_path = "/tmp/"
            index_name = "financial_ai_index"
            vectorstore.save_local(folder_path=temp_path, index_name=index_name)

            faiss_file = f"{temp_path}{index_name}.faiss"
            pkl_file = f"{temp_path}{index_name}.pkl"

            success = (
                    self.upload_to_s3(faiss_file, "financial_ai_index.faiss") and
                    self.upload_to_s3(pkl_file, "financial_ai_index.pkl")
            )

            for file_path in [faiss_file, pkl_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)

            return success

        except Exception as e:
            st.error(f"❌ Gagal membuat vector store: {e}")
            return False

    def load_vector_store(self) -> bool:
        """Memuat vector store dari S3"""
        try:
            temp_path = "/tmp/"
            index_name = "financial_ai_index"
            faiss_file = f"{temp_path}{index_name}.faiss"
            pkl_file = f"{temp_path}{index_name}.pkl"

            if not (self.download_from_s3("financial_ai_index.faiss", faiss_file) and
                    self.download_from_s3("financial_ai_index.pkl", pkl_file)):
                return False

            self.vectorstore = FAISS.load_local(
                folder_path=temp_path,
                index_name=index_name,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )

            return True

        except Exception as e:
            st.error(f"❌ Gagal memuat vector store: {e}")
            return False

    def get_financial_response(self, question: str) -> str:
        """Mendapatkan respons untuk pertanyaan keuangan"""
        if not self.vectorstore:
            return "❌ Vector store belum dimuat. Silakan upload dokumen terlebih dahulu."

        if not question.strip():
            return "Silakan masukkan pertanyaan yang valid."

        prompt_template = """
        Human: Anda adalah asisten AI yang ahli dalam analisis keuangan. Gunakan konteks yang diberikan untuk menjawab pertanyaan tentang laporan keuangan dengan akurat dan profesional.

        Jika pertanyaan meminta:
        - Angka/nilai: Berikan nilai yang tepat dengan format yang jelas
        - Analisis: Berikan interpretasi yang mendalam
        - Perbandingan: Tunjukkan perbedaan dan tren
        - Rekomendasi: Berikan saran berdasarkan data

        Jika tidak tahu jawabannya, katakan dengan jujur bahwa informasi tidak tersedia dalam dokumen.

        <context>
        {context}
        </context>

        Pertanyaan: {question}

        Assistant:"""

        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )

        qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 7}
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )

        try:
            result = qa({"query": question})
            return result["result"]
        except Exception as e:
            return f"❌ Error saat memproses pertanyaan: {e}"

    def create_pdf_report(self, content: str, title: str = "Financial Analysis Report") -> BytesIO:
        """Membuat laporan PDF"""
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, height - 50, title)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, height - 70, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        y = height - 100
        pdf.setFont("Helvetica", 10)

        for line in content.split("\n"):
            if y < 50:
                pdf.showPage()
                y = height - 50

            if len(line) > 80:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + word) < 80:
                        current_line += word + " "
                    else:
                        pdf.drawString(50, y, current_line.strip())
                        y -= 15
                        current_line = word + " "
                        if y < 50:
                            pdf.showPage()
                            y = height - 50
                if current_line:
                    pdf.drawString(50, y, current_line.strip())
                    y -= 15
            else:
                pdf.drawString(50, y, line)
                y -= 15

        pdf.save()
        buffer.seek(0)
        return buffer


def render_sidebar():
    """Render sidebar dengan chat sessions dan document upload"""
    st.sidebar.title("💰 Financial AI")

    # Chat Sessions Management
    st.sidebar.subheader("💬 Chat Sessions")

    # New Chat Button
    if st.sidebar.button("➕ New Chat", use_container_width=True):
        new_session_id = st.session_state.chat_manager.create_new_session()
        st.session_state.current_session_id = new_session_id
        st.rerun()

    # Sync controls
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("☁️ Sync to S3", help="Manually sync to S3"):
            if st.session_state.chat_manager.force_sync():
                st.sidebar.success("✅ Synced!")
            else:
                st.sidebar.error("❌ Sync failed")

    with col2:
        if st.button("📊 Stats", help="Show chat statistics"):
            stats = st.session_state.chat_manager.get_chat_statistics()
            st.sidebar.info(f"""
            **Chat Statistics:**
            - Sessions: {stats['total_sessions']}
            - Messages: {stats['total_messages']}
            - User: {stats['messages_by_role'].get('user', 0)}
            - AI: {stats['messages_by_role'].get('assistant', 0)}
            """)

    # List existing sessions
    sessions = st.session_state.chat_manager.get_all_sessions()

    if sessions:
        st.sidebar.markdown("**Recent Chats:**")
        for session in sessions[:10]:  # Show only recent 10
            session_title = session['title']
            session_id = session['id']

            col1, col2 = st.sidebar.columns([3, 1])

            with col1:
                if st.button(
                        session_title,
                        key=f"session_{session_id}",
                        use_container_width=True,
                        type="primary" if session_id == st.session_state.get('current_session_id') else "secondary"
                ):
                    st.session_state.current_session_id = session_id
                    st.rerun()

            with col2:
                if st.button("🗑️", key=f"delete_{session_id}"):
                    st.session_state.chat_manager.delete_session(session_id)
                    if session_id == st.session_state.get('current_session_id'):
                        st.session_state.current_session_id = None
                    st.rerun()

    st.sidebar.divider()

    # Export/Import Section
    st.sidebar.subheader("📤 Export/Import")

    if st.sidebar.button("📥 Export All Chats"):
        export_data = st.session_state.chat_manager.export_chat_history()
        export_json = json.dumps(export_data, indent=2, default=str)
        st.sidebar.download_button(
            label="💾 Download JSON",
            data=export_json,
            file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

    st.sidebar.divider()

    # Document Upload Section
    st.sidebar.subheader("📄 Upload Document")

    uploaded_file = st.sidebar.file_uploader(
        "Upload financial report",
        type=["pdf", "csv", "xlsx"],
        help="Supported: PDF, CSV, Excel"
    )

    if uploaded_file is not None:
        with st.spinner("Processing document..."):
            file_ext = uploaded_file.name.split(".")[-1].lower()
            temp_file_path = f"/tmp/{st.session_state.ai.get_unique_id()}.{file_ext}"

            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            documents = st.session_state.ai.process_financial_document(temp_file_path, file_ext)

            if documents:
                st.sidebar.success(f"✅ Loaded {len(documents)} documents")
                split_docs = st.session_state.ai.split_documents(documents)
                st.sidebar.info(f"📝 Split into {len(split_docs)} chunks")

                if st.session_state.ai.create_vector_store(split_docs):
                    st.sidebar.success("✅ Document processed and saved!")
                    st.session_state.vectorstore_loaded = True
                    st.session_state.ai.load_vector_store()
                else:
                    st.sidebar.error("❌ Failed to process document")

            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    # Load existing documents
    if st.sidebar.button("🔄 Load Saved Documents"):
        with st.spinner("Loading documents..."):
            if st.session_state.ai.load_vector_store():
                st.sidebar.success("✅ Documents loaded!")
                st.session_state.vectorstore_loaded = True
            else:
                st.sidebar.error("❌ No saved documents found")


def render_chat_interface():
    """Render main chat interface"""

    # Check if we have a current session
    if not st.session_state.get('current_session_id'):
        st.markdown("""
        <div style="text-align: center; padding: 100px 20px;">
            <h1>💰 Magnus Financial AI Assistant</h1>
            <p style="font-size: 18px; color: #666;">
                Welcome to your intelligent financial analysis assistant
            </p>
            <p style="color: #888;">
                Click "➕ New Chat" in the sidebar to start a conversation
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Get current session messages
    messages = st.session_state.chat_manager.get_session_messages(st.session_state.current_session_id)

    # Display chat messages
    for message in messages:
        if message['role'] == 'user':
            with st.chat_message("user"):
                st.write(message['content'])
        else:
            with st.chat_message("assistant"):
                st.write(message['content'])

                # Add download button for AI responses
                if st.button(f"📥 Download PDF", key=f"download_{message['timestamp']}"):
                    pdf_buffer = st.session_state.ai.create_pdf_report(
                        message['content'],
                        f"Financial Analysis - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    st.download_button(
                        label="📄 Download Report",
                        data=pdf_buffer,
                        file_name=f"financial_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )

    # Chat input
    if prompt := st.chat_input("Ask about your financial data..."):
        if not st.session_state.vectorstore_loaded:
            st.error("⚠️ Please upload a financial document first")
            return

        # Add user message to chat
        with st.chat_message("user"):
            st.write(prompt)

        # Save user message
        st.session_state.chat_manager.add_message(
            st.session_state.current_session_id, 'user', prompt
        )

        # Generate and display AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = st.session_state.ai.get_financial_response(prompt)
                st.write(response)

        # Save AI response
        st.session_state.chat_manager.add_message(
            st.session_state.current_session_id, 'assistant', response
        )

        # Auto-generate session title from first question
        if len(messages) == 0:  # First message in session
            title = prompt[:50] + "..." if len(prompt) > 50 else prompt
            st.session_state.chat_manager.update_session_title(
                st.session_state.current_session_id, title
            )

        st.rerun()


def main():
    st.set_page_config(
        page_title="Financial AI Assistant",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better UI
    st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
    }

    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }

    .user-message {
        background-color: #e3f2fd;
    }

    .assistant-message {
        background-color: #f5f5f5;
    }

    .stChatInput > div {
        border-radius: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'ai' not in st.session_state:
        st.session_state.ai = FinancialAI()
    if 'chat_manager' not in st.session_state:
        st.session_state.chat_manager = ChatManager()
    if 'vectorstore_loaded' not in st.session_state:
        st.session_state.vectorstore_loaded = False

    # Render UI
    render_sidebar()
    render_chat_interface()


if __name__ == "__main__":
    main()


from tabulate import tabulate

def print_all_tables():
    print("📋 Menampilkan semua variabel bertipe list/dict:\n")
    for name, val in globals().items():
        if name.startswith("__") or callable(val):
            continue

        print(f"\n🔹 {name}")
        if isinstance(val, dict):
            print(tabulate(val.items(), headers=["Key", "Value"], tablefmt="github"))
        elif isinstance(val, list):
            if all(isinstance(item, dict) for item in val):
                print(tabulate(val, headers="keys", tablefmt="github"))
            elif all(not isinstance(item, (list, dict)) for item in val):
                print(tabulate([[item] for item in val], headers=[name], tablefmt="github"))
            else:
                print(tabulate(val, tablefmt="github"))

# Panggil fungsi untuk menampilkan tabel
print_all_tables()
