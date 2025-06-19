![Magnus_AI_Project.png](Magnus_AI_Project.png)

```bash
pip install -r requirements.txt
```

```bash
streamlit run main.py
```

## Tujuan Utama Skrip

Skrip ini adalah chat interface AI berbasis dokumen PDF, dibangun menggunakan LangChain, Streamlit, dan Bedrock (AWS). Data chat disimpan di SQLite dan disinkronkan ke S3.

## Komponen Utama & Penjelasannya

### LangChain Modules

Digunakan untuk memproses dokumen dan membuat RAG (Retrieval-Augmented Generation).

BedrockEmbeddings: Membuat vektor embedding dari teks menggunakan Amazon Bedrock (model foundation).

FAISS: Library untuk menyimpan dan mencari vektor. Dipakai untuk pencarian semantik cepat.

Hasil dari proses ini biasanya disimpan dalam file .faiss dan .pkl:

.faiss: menyimpan index FAISS.

.pkl: menyimpan metadata (contohnya teks asli atau ID-nya).

PyPDFLoader: Untuk memuat konten dari PDF ke dalam format yang bisa diproses.

RecursiveCharacterTextSplitter: Memecah teks panjang menjadi potongan kecil yang lebih mudah diproses oleh LLM.

### Streamlit

Biasanya digunakan untuk:
- Upload PDF
- Menampilkan chat
- Menjalankan pertanyaan ke model

### SQLite (chat_sessions dan chat_messages)

Dua tabel disiapkan untuk menyimpan riwayat percakapan:
- chat_sessions: metadata setiap sesi chat.
- chat_messages: isi dari setiap percakapan, dengan referensi ke sesi-nya.

### AWS S3 Sync

Variabel BUCKET_NAME dan CHAT_DB_S3_KEY dipakai untuk:
- download_file: mengambil financial_ai_chats.db dari S3.
- upload_file: mengunggah hasil update kembali ke S3.

### ChatManager Class

Menangani:
- Sinkronisasi database dari/ke S3
- Inisialisasi database SQLite
- Mungkin juga mengatur insert/delete untuk chat (belum terlihat semua)

## File Output & Fungsinya

| File                    | Fungsi                                              |
| ----------------------- | --------------------------------------------------- |
| `.faiss`                | Index untuk pencarian vektor FAISS                  |
| `.pkl`                  | Metadata terkait dokumen / chunk / mapping          |
| `financial_ai_chats.db` | Menyimpan data chat user secara lokal               |
| (PDF files)             | Diunggah oleh user untuk dijadikan dasar pertanyaan |

## Alur Umum Aplikasi

User upload PDF via Streamlit.
1. Teks di-split jadi chunk kecil → dibuat embedding dengan Bedrock.
2. Embeddings disimpan di FAISS index (.faiss + .pkl).
3. User bertanya → sistem cari chunk paling relevan → kirim ke LLM.
4. Jawaban & history disimpan di SQLite → di-sync ke S3.