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
        
        MLFLOW_TRACKING_URI = 'http://172.17.0.1:5000' 
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Unit Test & Coverage') {
            steps {
                script {
                    sh "docker build -f docker/Dockerfile.ci -t hallucination-ci:latest ."
                    sh "docker run --rm hallucination-ci:latest"
                }
            }
        }

        stage('Provision Infra (IaC)') {
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: "${SSH_KEY_ID}", keyFileVariable: 'SSH_KEY'),
                    file(credentialsId: "${KUBE_ID}", variable: 'KUBECONFIG_FILE')
                ]) {
                    script {
                        withEnv(["KUBECONFIG=${KUBECONFIG_FILE}"]) {
                            
                            echo "Verify Connection to Minikube"
                            sh "kubectl cluster-info"
                            
                            echo "Running Terraform"
                            dir('iac/terraform') {
                                sh "terraform init && terraform apply -auto-approve"
                            }
                            
                            echo "Running Ansible Stack"
                            dir('iac/ansible') {
                                sh """
                                # Cài đặt collection cần thiết cho K8s
                                ansible-galaxy collection install kubernetes.core
                                export ANSIBLE_HOST_KEY_CHECKING=False
                                
                                # Chạy playbook với file KUBECONFIG đã nhúng
                                ansible-playbook -i inventory.ini setup_k8s_stack.yml \
                                --private-key=${SSH_KEY} \
                                --extra-vars "kubeconfig_path=${KUBECONFIG_FILE}"
                                """
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
                withCredentials([
                    string(credentialsId: "${HF_TOKEN_ID}", variable: 'HF_TOKEN'),
                    file(credentialsId: "${KUBE_ID}", variable: 'KUBECONFIG_FILE')
                ]) {
                    script {
                        withEnv(["KUBECONFIG=${KUBECONFIG_FILE}"]) {
                            sh """
                            helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                            --namespace ${K8S_NAMESPACE} \
                            --create-namespace \
                            --set image.tag=${env.BUILD_NUMBER} \
                            --set image.repository=${FULL_IMAGE} \
                            --set secrets.hfToken=${HF_TOKEN} \
                            --wait --timeout 5m
                            """
                        }
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