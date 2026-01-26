pipeline {
    agent any
    
    environment {
        KUBE_ID = 'kubeconfig-minikube'
        DOCKER_ID = 'docker-hub-credentials'
        HF_TOKEN_ID = 'huggingface-token'
        SSH_KEY_ID = 'ubuntu-ssh-key'

        DOCKER_REGISTRY_USER = 'nhnammldlnlpcvrs'
        DOCKER_IMAGE_NAME = 'vietnamese-llm-hallucination-detection'
        FULL_IMAGE = "${DOCKER_REGISTRY_USER}/${DOCKER_IMAGE_NAME}"
        
        K8S_NAMESPACE = 'hallucination-prod'
        HELM_RELEASE = 'hallucination-app'
        HELM_CHART_PATH = './kubernetes/charts/hallucination-backend'
        
        MLFLOW_TRACKING_URI = 'http://host.docker.internal:5000' 
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
                sh "pip install --no-cache-dir -r requirements-ci.txt pytest-cov mlflow"
                withEnv(['PYTHONPATH=.']) {
                    sh "pytest tests/unit --cov=backend --cov-report=xml --cov-fail-under=80"
                }
            }
        }

        stage('Provision Infra (IaC)') {
            steps {
                sshagent([SSH_KEY_ID]) {
                    withKubeConfig([credentialsId: "${KUBE_ID}"]) {
                        script {
                            echo "Terraform applying..."
                            dir('iac/terraform') {
                                sh "terraform init && terraform apply -auto-approve"
                            }
                            
                            echo "Ansible configuring..."
                            dir('iac/ansible') {
                                sh "export ANSIBLE_HOST_KEY_CHECKING=False && ansible-playbook -i inventory.ini setup_k8s_stack.yml"
                            }
                        }
                    }
                }
            }
        }

        stage('Build & Push Docker') {
            steps {
                script {
                    echo "Pulling model artifacts..."
                    sh "export MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI} && python3 -m mlflow artifacts download --artifact-uri models:/hallu-model/latest --dst ./models/phobert_finetuned_model"

                    sh "docker build -f docker/Dockerfile.backend -t ${FULL_IMAGE}:${env.BUILD_NUMBER} ."
                    
                    withDockerRegistry([credentialsId: "${DOCKER_ID}", url: '']) {
                        sh "docker push ${FULL_IMAGE}:${env.BUILD_NUMBER}"
                        sh "docker tag ${FULL_IMAGE}:${env.BUILD_NUMBER} ${FULL_IMAGE}:latest"
                        sh "docker push ${FULL_IMAGE}:latest"
                    }
                }
            }
        }

        stage('Deploy to K8s') {
            steps {
                withCredentials([string(credentialsId: "${HF_TOKEN_ID}", variable: 'HF_TOKEN')]) {
                    withKubeConfig([credentialsId: "${KUBE_ID}"]) {
                        sh """
                        helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                        --namespace ${K8S_NAMESPACE} \
                        --create-namespace \
                        --set image.tag=${env.BUILD_NUMBER} \
                        --set image.repository=${FULL_IMAGE} \
                        --set secrets.hfToken=${HF_TOKEN} \
                        --wait
                        """
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}