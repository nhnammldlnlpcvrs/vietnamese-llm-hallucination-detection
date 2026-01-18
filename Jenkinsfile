pipeline {
    agent any
    
    environment {
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

        stage('Build & Push Docker') {
            steps {
                script {
                    echo "--- Building Docker Image ---"
                    sh "docker build -f docker/Dockerfile.serving -t ${DOCKER_IMAGE}:${env.BUILD_NUMBER} ."
                    
                    echo "--- Pushing to Docker Hub ---"
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
                    input message: 'Image Built. Deploy to Local K8s?', ok: 'Deploy Now'
                }
            }
        }

        stage('Deploy to K8s') {
            steps {
                script {
                    echo "--- Deploying with Helm ---"
                    sh """
                    helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                        --namespace ${K8S_NAMESPACE} \
                        --create-namespace \
                        --set image.tag=${env.BUILD_NUMBER} \
                        --set image.repository=${DOCKER_IMAGE} \
                        --set model.enabled=false \
                        --wait
                    """
                }
            }
        }
    }
}