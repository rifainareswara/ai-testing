# 🚀 Panduan Deployment Financial AI ke BytePlus Kubernetes

## 📁 Struktur File yang Akan Dibuat

Buat folder baru untuk project Kubernetes Anda:

```
financial-ai-k8s/
├── 01-namespace.yaml       # Namespace untuk project
├── 02-configmap.yaml       # Konfigurasi non-sensitif
├── 04-deployment.yaml      # Definisi aplikasi
├── 05-service.yaml         # Network service
├── 06-ingress.yaml         # Domain routing (opsional)
├── 07-hpa.yaml            # Auto-scaling (opsional)
├── .env                   # File environment variables
└── deploy.sh              # Script deployment otomatis
```

## 🛠️ LANGKAH 1: Persiapan Environment

### 1.1 Install kubectl
```bash
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Mac
brew install kubectl

# Windows (dengan Chocolatey)
choco install kubernetes-cli
```

### 1.2 Setup BytePlus Container Registry
1. **Login ke BytePlus Console**
2. **Buat Container Registry:**
   - Menu: Container Service → Container Registry
   - Klik "Create Repository"
   - Repository Name: `financial-ai`
   - Access Level: Private
   - Region: Asia Pacific (Singapore) - ap-southeast-3

### 1.3 Setup BytePlus VKE Cluster
1. **Buat Kubernetes Cluster:**
   - Menu: Container Service → Vital Kubernetes Engine
   - Klik "Create Cluster"
   - Cluster Name: `financial-ai-cluster`
   - Version: Latest available
   - Node Group: Pilih instance type sesuai kebutuhan
   - Node Count: 2-3 nodes

2. **Download Kubeconfig:**
   - Setelah cluster ready, klik cluster name
   - Tab "Basic Information"
   - Klik "Download" pada Kubeconfig

## 🐳 LANGKAH 2: Build dan Push Docker Image

### 2.1 Login ke Container Registry
```bash
# Dapatkan login command dari BytePlus Console
# Container Registry → Your Repository → View Push Command
docker login cr-ap-southeast-3.byteplusapi.com
```

### 2.2 Build dan Push Image
```bash
# Pastikan Anda berada di folder aplikasi (yang ada Dockerfile)
cd /path/to/your/financial-ai-app

# Build image
docker build -t financial-ai:latest .

# Tag untuk BytePlus Registry
# GANTI 'your-namespace' dengan namespace BytePlus Anda
docker tag financial-ai:latest cr-ap-southeast-3.byteplusapi.com/your-namespace/financial-ai:latest

# Push image
docker push cr-ap-southeast-3.byteplusapi.com/your-namespace/financial-ai:latest
```

### 2.3 Verify Image
```bash
# Cek di BytePlus Console → Container Registry
# Pastikan image sudah ter-upload
```

## ⚙️ LANGKAH 3: Konfigurasi kubectl

### 3.1 Setup Kubeconfig
```bash
# Copy kubeconfig yang didownload ke ~/.kube/
mkdir -p ~/.kube
cp /path/to/downloaded/kubeconfig ~/.kube/config

# Atau set temporary
export KUBECONFIG=/path/to/kubeconfig

# Test koneksi
kubectl cluster-info
kubectl get nodes
```

## 📝 LANGKAH 4: Siapkan File Kubernetes

### 4.1 Buat Folder Project
```bash
mkdir financial-ai-k8s
cd financial-ai-k8s
```

### 4.2 Copy File .env
```bash
# Copy file .env dari project aplikasi Anda
cp /path/to/your/app/.env .

# Atau buat manual
cat > .env << EOF
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
API_KEY=your_api_key
# Tambahkan variable lain sesuai kebutuhan
EOF
```

### 4.3 Buat File YAML
Salin semua file YAML dari artifact di atas, simpan dengan nama:

1. **01-namespace.yaml** - Copy isi namespace section
2. **02-configmap.yaml** - Copy isi configmap section  
3. **04-deployment.yaml** - Copy isi deployment section
4. **05-service.yaml** - Copy isi service section
5. **06-ingress.yaml** - Copy isi ingress section (opsional)
6. **07-hpa.yaml** - Copy isi HPA section (opsional)

### 4.4 Edit deployment.yaml
**PENTING:** Ganti URL image di file `04-deployment.yaml`:

```yaml
# Cari baris ini:
image: cr-ap-southeast-3.byteplusapi.com/YOUR_NAMESPACE/financial-ai:latest

# Ganti YOUR_NAMESPACE dengan namespace BytePlus Anda
image: cr-ap-southeast-3.byteplusapi.com/actual-namespace/financial-ai:latest
```

## 🚀 LANGKAH 5: Deploy ke Kubernetes

### 5.1 Deploy Manual (Step by Step)
```bash
# 1. Buat namespace
kubectl apply -f 01-namespace.yaml

# 2. Buat configmap
kubectl apply -f 02-configmap.yaml

# 3. Buat secret dari file .env
kubectl create secret generic financial-ai-secret \
  --from-env-file=.env \
  --namespace=financial-ai

# 4. Deploy aplikasi
kubectl apply -f 04-deployment.yaml

# 5. Buat service
kubectl apply -f 05-service.yaml

# 6. (Opsional) Deploy ingress dan HPA
kubectl apply -f 06-ingress.yaml
kubectl apply -f 07-hpa.yaml
```

### 5.2 Deploy Otomatis dengan Script
Buat file `deploy.sh`:

```bash
#!/bin/bash
echo "🚀 Starting deployment of Financial AI to BytePlus Kubernetes..."

# Apply namespace
echo "📁 Creating namespace..."
kubectl apply -f 01-namespace.yaml

# Apply configmap
echo "⚙️ Creating configmap..."
kubectl apply -f 02-configmap.yaml

# Create secret from .env file
echo "🔐 Creating secret..."
kubectl create secret generic financial-ai-secret \
  --from-env-file=.env \
  --namespace=financial-ai \
  --dry-run=client -o yaml | kubectl apply -f -

# Apply deployment
echo "🏗️ Deploying application..."
kubectl apply -f 04-deployment.yaml

# Apply service
echo "🌐 Creating service..."
kubectl apply -f 05-service.yaml

# Apply ingress (optional)
echo "🔗 Creating ingress..."
kubectl apply -f 06-ingress.yaml

# Apply HPA (optional)
echo "📈 Creating auto-scaler..."
kubectl apply -f 07-hpa.yaml

echo "✅ Deployment completed!"
echo "📊 Checking status..."
kubectl get all -n financial-ai
```

Jalankan script:
```bash
chmod +x deploy.sh
./deploy.sh
```

## ✅ LANGKAH 6: Verifikasi Deployment

### 6.1 Cek Status Deployment
```bash
# Lihat semua resource
kubectl get all -n financial-ai

# Cek status pods
kubectl get pods -n financial-ai

# Lihat detail pod (jika ada masalah)
kubectl describe pod [POD-NAME] -n financial-ai

# Lihat logs aplikasi
kubectl logs -f deployment/financial-ai-deployment -n financial-ai
```

### 6.2 Cek Service
```bash
# Lihat service dan external IP
kubectl get service -n financial-ai

# Tunggu sampai EXTERNAL-IP muncul (bukan <pending>)
kubectl get service financial-ai-service -n financial-ai -w
```

## 🌐 LANGKAH 7: Akses Aplikasi

### 7.1 Melalui LoadBalancer (Recommended)
```bash
# Dapatkan external IP
kubectl get service financial-ai-service -n financial-ai

# Output contoh:
# NAME                    TYPE           CLUSTER-IP     EXTERNAL-IP      PORT(S)        AGE
# financial-ai-service    LoadBalancer   10.100.X.X     203.XXX.XXX.XXX  80:32000/TCP   5m

# Akses aplikasi di browser:
# http://EXTERNAL-IP
```

### 7.2 Melalui Port Forwarding (untuk Testing)
```bash
# Forward port dari service ke local
kubectl port-forward service/financial-ai-service 8501:80 -n financial-ai

# Akses di browser:
# http://localhost:8501
```

## 🔧 LANGKAH 8: Monitoring dan Troubleshooting

### 8.1 Commands Monitoring
```bash
# Status pods realtime
kubectl get pods -n financial-ai -w

# Resource usage
kubectl top pods -n financial-ai
kubectl top nodes

# Events (untuk debugging)
kubectl get events -n financial-ai --sort-by=.metadata.creationTimestamp

# Logs aplikasi
kubectl logs -f deployment/financial-ai-deployment -n financial-ai
```

### 8.2 Troubleshooting Common Issues

#### Pod dalam status ImagePullBackOff
```bash
# Cek detail error
kubectl describe pod [POD-NAME] -n financial-ai

# Kemungkinan masalah:
# - URL image salah
# - Image tidak ada di registry
# - Registry authentication gagal
```

#### Pod dalam status CrashLoopBackOff  
```bash
# Lihat logs untuk error
kubectl logs [POD-NAME] -n financial-ai

# Kemungkinan masalah:
# - Environment variables tidak ada
# - Port salah
# - Dependency tidak tersedia
```

#### Service tidak bisa diakses
```bash
# Cek endpoints
kubectl get endpoints -n financial-ai

# Test dari dalam cluster
kubectl run test-pod --image=busybox --rm -it --restart=Never -- sh
# Dalam pod test, jalankan:
# wget -qO- http://financial-ai-service.financial-ai:80
```

## 📋 LANGKAH 9: Update Aplikasi

### 9.1 Update Image
```bash
# Build image baru dengan tag baru
docker build -t financial-ai:v2 .
docker tag financial-ai:v2 cr-ap-southeast-3.byteplusapi.com/your-namespace/financial-ai:v2
docker push cr-ap-southeast-3.byteplusapi.com/your-namespace/financial-ai:v2

# Update deployment
kubectl set image deployment/financial-ai-deployment \
  financial-ai-container=cr-ap-southeast-3.byteplusapi.com/your-namespace/financial-ai:v2 \
  -n financial-ai

# Monitor rollout
kubectl rollout status deployment/financial-ai-deployment -n financial-ai
```

### 9.2 Update ConfigMap
```bash
# Edit configmap
kubectl edit configmap financial-ai-config -n financial-ai

# Restart deployment untuk apply perubahan
kubectl rollout restart deployment/financial-ai-deployment -n financial-ai
```

## 🗑️ LANGKAH 10: Cleanup (Jika Diperlukan)

```bash
# Hapus semua resource di namespace
kubectl delete namespace financial-ai

# Atau hapus satu per satu
kubectl delete -f 07-hpa.yaml
kubectl delete -f 06-ingress.yaml
kubectl delete -f 05-service.yaml
kubectl delete -f 04-deployment.yaml
kubectl delete secret financial-ai-secret -n financial-ai
kubectl delete -f 02-configmap.yaml
kubectl delete -f 01-namespace.yaml
```

## 🎉 Selesai!

Aplikasi Financial AI Anda sekarang sudah berjalan di BytePlus Kubernetes! 

### Quick Reference Commands:
```bash
# Status semua resource
kubectl get all -n financial-ai

# Logs aplikasi
kubectl logs -f deployment/financial-ai-deployment -n financial-ai

# Port forward untuk testing
kubectl port-forward service/financial-ai-service 8501:80 -n financial-ai

# Scale aplikasi
kubectl scale deployment financial-ai-deployment --replicas=3 -n financial-ai
```