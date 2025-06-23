Dari data yang Anda berikan, berikut beberapa jenis pertanyaan untuk menguji AI yang Anda buat. Pertanyaan ini mencakup pemahaman, perhitungan, dan analisis dari data pada sheet Revenue dan Cost, cocok untuk menguji kemampuan reasoning dan query comprehension LLM:

⸻

📊 Pertanyaan dari Sheet “Revenue”
	1.	Berapa total pemasukan (Amount Inc PPN) dari semua invoice yang diterbitkan pada tahun 2025?
	2.	Sebutkan nama pelanggan yang paling sering muncul dalam data revenue.
	3.	Hitung total PPH dan PPN yang dibayarkan dari seluruh transaksi.
	4.	Berapa jumlah invoice yang belum dibayar (lihat Sisa Saldo > 0)?
	5.	Dari semua data, project kode mana yang paling sering muncul?
	6.	Apa jenis layanan (Services Type) yang paling banyak menghasilkan pemasukan?
	7.	Berapa total pembayaran (Pembayaran) yang sudah diterima hingga bulan Juni 2025?
	8.	Berikan daftar invoice yang termasuk dalam kategori Aging Buckets = “0-30 Days”.
	9.	Berapa rata-rata jumlah pembayaran yang diterima untuk tiap invoice yang telah dibayar penuh?

⸻

📉 Pertanyaan dari Sheet “Cost”
	1.	Berapa total pengeluaran (TOTAL AFTER VAT) untuk supplier bernama Meta Platforms Ireland Limited?
	2.	Sebutkan invoice dari supplier yang belum dibayar (TGL BAYAR masih kosong)?
	3.	Invoice mana saja yang sesuai dengan kode project TS2402020 dan sudah dibayar?
	4.	Berapa total nilai PPN yang dibayarkan untuk semua transaksi di tahun 2025?
	5.	Apa PO (purchase order) yang memiliki nominal pengeluaran tertinggi (TOTAL AFTER VAT)?
	6.	Berapa rata-rata pengeluaran sebelum pajak (BEFORE VAT)?
	7.	Invoice ke client mana yang berhubungan dengan invoice supplier terbesar?
	8.	Tampilkan aging buckets mana yang paling sering muncul dalam transaksi biaya.
	9.	Berapa total PPH yang seharusnya dibayarkan jika semua memiliki tarif 0.2?

⸻

🧠 Pertanyaan Analisis Gabungan
	1.	Berapa profit bersih (Revenue - Cost) dari project TS2402020 hingga Juni 2025?
	2.	Dari semua data, berapa rasio antara total pemasukan dan total pengeluaran?
	3.	Apakah semua invoice revenue memiliki pasangan invoice cost (berdasarkan No Invoice atau Kode Project)?
	4.	Apakah ada proyek yang menghasilkan revenue tapi tidak memiliki cost?
	5.	Buat ringkasan pendapatan dan pengeluaran bulanan dari Januari hingga Juni 2025.

⸻

Jika Anda ingin saya bantu membuat kode Python untuk menguji AI dengan jawaban dari data tersebut atau membuat API testing scenario, tinggal beri tahu ya! ￼