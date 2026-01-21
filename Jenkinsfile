pipeline {
    agent any
    
    environment {
        KUBECONFIG = '/var/jenkins_home/.kube/config'
        
        DOCKER_REGISTRY_USER = 'nhnammldlnlpcvrs'
        DOCKER_IMAGE_NAME = 'vietnamese-llm-hallucination-detection'
        FULL_IMAGE = "${DOCKER_REGISTRY_USER}/${DOCKER_IMAGE_NAME}"
        
        K8S_NAMESPACE = 'hallucination-prod'
        HELM_RELEASE = 'hallucination-app'
        
        HELM_CHART_PATH = './kubernetes/charts/hallucination-backend' 
        HELM_VALUES_FILE = './kubernetes/values/backend-prod.yaml'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
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
                    echo "Installing Dependencies"
                    sh "pip install --no-cache-dir -r requirements-ci.txt"
                    sh "pip install pytest-cov"
                    
                    echo "Running Tests"
                    try {
                        withEnv(['PYTHONPATH=.']) {
                            sh "pytest tests/unit --cov=backend --cov-report=term-missing --cov-fail-under=80"
                        }
                    } catch (Exception e) {
                        echo "TEST FAILED or COVERAGE LOW"
                        error "Pipeline stopped: Coverage < 80% or Tests Failed."
                    }
                }
            }
        }

        stage('Build & Push Docker') {
            steps {
                script {
                    echo "Building Docker Image"
                    sh "docker build -f docker/Dockerfile.backend -t ${FULL_IMAGE}:${env.BUILD_NUMBER} ."
                    
                    echo "Pushing to Docker Hub"
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
                script {
                    input message: 'Tests & Build Passed. Deploy to Production K8s?', ok: 'Deploy Now'
                }
            }
        }

        stage('Deploy to K8s') {
            steps {
                script {
                    echo "Deploying with Helm"
                    sh """
                    helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                        --namespace ${K8S_NAMESPACE} \
                        --create-namespace \
                        --set image.tag=${env.BUILD_NUMBER} \
                        --set image.repository=${FULL_IMAGE} \
                        --set model.enabled=false \
                        --set service.type=NodePort \
                        --set service.nodePort=30005 \
                        --wait
                    """
                }
            }
        }
    }
}