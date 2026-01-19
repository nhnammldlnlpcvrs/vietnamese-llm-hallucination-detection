pipeline {
    agent any
    
    environment {
        KUBECONFIG = '/var/jenkins_home/.kube/config'
        
        DOCKER_IMAGE = 'nhnammldlnlpcvrs/vietnamese-llm-hallucination-detection'
        K8S_NAMESPACE = 'hallucination-prod'
        HELM_RELEASE = 'hallucination-app'
        HELM_CHART_PATH = './helm/hallucination-chart'
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
                    image 'python:3.9-slim' 
                    args '-u 0:0'
                }
            }
            steps {
                script {
                    echo "1. Installing Light Dependencies"
                    sh "pip install --no-cache-dir -r requirements-test.txt"
                    
                    echo "2. Running Tests"
                    try {
                        withEnv(['PYTHONPATH=.']) {
                            sh "pytest --cov=backend --cov-report=term-missing --cov-fail-under=80 tests/unit/"
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
                    sh "docker build -f docker/Dockerfile.serving -t ${DOCKER_IMAGE}:${env.BUILD_NUMBER} ."
                    
                    echo "Pushing to Docker Hub"
                    withDockerRegistry([credentialsId: 'docker-hub-credentials', url: '']) {
                        sh "docker push ${DOCKER_IMAGE}:${env.BUILD_NUMBER}"
                        sh "docker tag ${DOCKER_IMAGE}:${env.BUILD_NUMBER} ${DOCKER_IMAGE}:latest"
                        sh "docker push ${DOCKER_IMAGE}:latest"
                    }
                }
            }
        }

        stage('Manual Approval') {
            steps {
                script {
                    input message: 'Tests Passed. Deploy to K8s?', ok: 'Deploy Now'
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
                        --set image.repository=${DOCKER_IMAGE} \
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