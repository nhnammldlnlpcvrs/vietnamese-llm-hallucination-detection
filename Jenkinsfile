pipeline {
    agent any

    environment {
        KUBE_ID       = 'kubeconfig-minikube'
        DOCKER_ID     = 'docker-hub-credentials'
        HF_TOKEN_ID   = 'huggingface-token'
        SSH_KEY_ID    = 'ubuntu-ssh-key'

        DOCKER_REGISTRY_USER = 'nhnammldlnlpcvrs'
        DOCKER_IMAGE_NAME    = 'vietnamese-llm-hallucination-detection'
        FULL_IMAGE           = "${DOCKER_REGISTRY_USER}/${DOCKER_IMAGE_NAME}"

        K8S_NAMESPACE   = 'hallucination-prod'
        HELM_RELEASE    = 'hallucination-app'
        HELM_CHART_PATH = './kubernetes/charts/hallucination-backend'

        MLFLOW_TRACKING_URI = 'http://localhost:5000'
        MODEL_NAME          = 'hallu-model'
        MODEL_STAGE         = 'Production'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Unit Test & Coverage') {
            steps {
                script {
                    sh '''
                    docker build -f docker/Dockerfile.ci -t hallucination-ci:latest .
                    docker run --rm hallucination-ci:latest
                    '''
                }
            }
        }

       stage('Provision Infra (IaC)') {
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: SSH_KEY_ID, keyFileVariable: 'SSH_KEY'),
                    file(credentialsId: KUBE_ID, variable: 'KUBECONFIG')
                ]) {
                    withEnv([
                        "ANSIBLE_K8S_AUTH_KUBECONFIG=$KUBECONFIG",
                        "TF_VAR_kube_config=$KUBECONFIG"
                    ]) {

                        sh "kubectl cluster-info"

                        dir('iac/terraform') {
                            sh '''
                            terraform init
                            terraform apply -auto-approve
                            '''
                        }

                        dir('iac/ansible') {
                            sh '''
                            pwd
                            ls -la

                            ansible-galaxy collection install kubernetes.core
                            export ANSIBLE_HOST_KEY_CHECKING=False

                            ansible-playbook \
                            -i inventory.ini \
                            setup_k8s_stack.yaml \
                            --private-key=$SSH_KEY \
                            --extra-vars "ansible_python_interpreter=/usr/bin/python3 kubeconfig_path=$KUBECONFIG"
                            '''
                        }
                    }
                }
            }
        }

        stage('Port-forward MLflow') {
            steps {
                script {
                    sh '''
                    echo "Starting MLflow port-forward..."
                    kubectl port-forward -n mlflow svc/mlflow 5000:80 >/tmp/mlflow_pf.log 2>&1 &
                    echo $! > /tmp/mlflow_pf.pid
                    sleep 10
                    curl -f http://localhost:5000 || (echo "MLflow not reachable" && exit 1)
                    '''
                }
            }
        }
        
        stage('Download Model Artifacts (MLflow)') {
            steps {
                retry(3) {
                    timeout(time: 5, unit: 'MINUTES') {
                        sh '''
                        echo "Downloading model from MLflow..."

                        rm -rf models/phobert_finetuned_model
                        mkdir -p models

                        docker run --rm \
                        + --network host \
                          -e MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI} \
                          -v $(pwd)/models:/models \
                          python:3.10-slim \
                        bash -c "
                            pip install --no-cache-dir mlflow && \
                            python -m mlflow artifacts download \
                            --artifact-uri models:/${MODEL_NAME}/${MODEL_STAGE} \
                            --dst-path /models/phobert_finetuned_model
                        "

                        test -f models/phobert_finetuned_model/config.json
                        echo 'Model download OK'
                        '''
                    }
                }
            }
        }


        stage('Build & Push Docker Image') {
            steps {
                script {
                    sh "docker build -f docker/Dockerfile.backend -t ${FULL_IMAGE}:${BUILD_NUMBER} ."

                    withDockerRegistry([credentialsId: "${DOCKER_ID}", url: '']) {
                        sh '''
                        docker push ${FULL_IMAGE}:${BUILD_NUMBER}
                        docker tag ${FULL_IMAGE}:${BUILD_NUMBER} ${FULL_IMAGE}:latest
                        docker push ${FULL_IMAGE}:latest
                        '''
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([
                    string(credentialsId: "${HF_TOKEN_ID}", variable: 'HF_TOKEN'),
                    file(credentialsId: "${KUBE_ID}", variable: 'KUBECONFIG_FILE')
                ]) {
                    withEnv(["KUBECONFIG=${KUBECONFIG_FILE}"]) {
                        script {
                            sh '''
                            helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                              --namespace ${K8S_NAMESPACE} \
                              --create-namespace \
                              --set image.repository=${FULL_IMAGE} \
                              --set image.tag=${BUILD_NUMBER} \
                              --set secrets.hfToken=${HF_TOKEN} \
                              --wait --timeout 5m

                            kubectl rollout status deployment/${HELM_RELEASE} -n ${K8S_NAMESPACE}
                            kubectl get pods -n ${K8S_NAMESPACE}
                            '''
                        }
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Deployment successful!"
        }
        failure {
            echo "Pipeline failed!"
        }
        always {
            sh '''
            if [ -f /tmp/mlflow_pf.pid ]; then
              kill $(cat /tmp/mlflow_pf.pid) || true
              rm -f /tmp/mlflow_pf.pid
            fi
            '''
            cleanWs()
        }
    }
}
