pipeline {
    agent any
    
    environment {
        KUBECONFIG = "/tmp/config-jenkins"
        DOCKER_REGISTRY_USER = 'nhnammldlnlpcvrs'
        DOCKER_IMAGE_NAME = 'vietnamese-llm-hallucination-detection'
        FULL_IMAGE = "${DOCKER_REGISTRY_USER}/${DOCKER_IMAGE_NAME}"
        
        K8S_NAMESPACE = 'hallucination-prod'
        HELM_RELEASE = 'hallucination-app'
        HELM_CHART_PATH = './kubernetes/charts/hallucination-backend'
        
        MLFLOW_TRACKING_URI = 'http://mlflow.observability:5000'
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Unit Test & Coverage') {
            agent {
                docker { 
                    image 'python:3.10-slim-bookworm'
                    args '-u 0:0'
                }
            }
            steps {
                script {
                    sh "pip install --no-cache-dir -r requirements-ci.txt pytest-cov mlflow"
                    withEnv(['PYTHONPATH=.']) {
                        sh "pytest tests/unit --cov=backend --cov-report=xml --cov-fail-under=80"
                    }
                }
            }
        }

        stage('Provision Infra (IaC)') {
            steps {
                script {
                    echo "Provisioning Cloud Cluster with Terraform..."
                    dir('iac/terraform') {
                        sh "terraform init && terraform apply -auto-approve"
                    }
                    
                    echo "Configuring K8s Stack (Istio, Knative, KServe) with Ansible..."
                    dir('iac/ansible') {
                        sh "ansible-playbook -i inventory.ini setup_k8s_stack.yml"
                    }
                }
            }
        }

        stage('Build & Push Docker') {
            steps {
                script {
                    echo "Pulling latest model artifacts from MLFlow..."
                    sh "export MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI} && python -m mlflow artifacts download --artifact-uri models:/hallu-model/latest --dst ./models/phobert_finetuned_model"

                    sh "docker build -f docker/Dockerfile.backend -t ${FULL_IMAGE}:${env.BUILD_NUMBER} ."
                    
                    withDockerRegistry([credentialsId: 'docker-hub-credentials', url: '']) {
                        sh "docker push ${FULL_IMAGE}:${env.BUILD_NUMBER}"
                        sh "docker tag ${FULL_IMAGE}:${env.BUILD_NUMBER} ${FULL_IMAGE}:latest"
                        sh "docker push ${FULL_IMAGE}:latest"
                    }
                }
            }
        }

        stage('Manual Approval') {
            steps {
                input message: "Build #${env.BUILD_NUMBER} passed tests. Deploy to Cloud K8s?"
            }
        }

        stage('Deploy to K8s') {
            steps {
                sh "kubectl config get-contexts" 
                sh """
                helm upgrade --install hallucination-app ./kubernetes/charts/hallucination-backend \
                --namespace hallucination-prod \
                --create-namespace \
                --set image.tag=${env.BUILD_NUMBER} \
                --set image.repository=nhnammldlnlpcvrs/vietnamese-llm-hallucination-detection \
                --set secrets.hfToken=${HF_TOKEN} \
                --kubeconfig /home/nguyen-nam/.kube/config \
                --wait
                """
            }
        }
    }
    
    post {
        always {
            echo "Cleaning up workspace..."
            cleanWs()
        }
    }
}