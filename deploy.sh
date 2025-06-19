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