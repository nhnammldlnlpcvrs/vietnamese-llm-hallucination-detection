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

        COVERAGE_THRESHOLD  = 80
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
                sh '''
                docker build -f docker/Dockerfile.ci -t hallucination-ci:latest .
                docker run --rm \
                hallucination-ci:latest \
                pytest tests/unit --cov=backend --cov-report=xml
                '''
            }
        }

        stage('Check Coverage Threshold') {
            steps {
                script {
                    def coverage = sh(
                        script: "grep -o 'line-rate=\"[0-9.]*\"' coverage.xml | head -1 | cut -d'\"' -f2",
                        returnStdout: true
                    ).trim().toFloat() * 100

                    echo "Detected coverage: ${coverage}%"

                    if (coverage < COVERAGE_THRESHOLD.toInteger()) {
                        error("Coverage below ${COVERAGE_THRESHOLD}% - stopping pipeline")
                    }
                }
            }
        }

        stage('Provision Infra (Terraform + Ansible)') {
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: SSH_KEY_ID, keyFileVariable: 'SSH_KEY'),
                    file(credentialsId: KUBE_ID, variable: 'KUBECONFIG'),
                    usernamePassword(
                        credentialsId: DOCKER_ID,
                        usernameVariable: 'GHCR_USERNAME',
                        passwordVariable: 'GHCR_TOKEN'
                    )
                ]) {
                    withEnv([
                        "ANSIBLE_K8S_AUTH_KUBECONFIG=$KUBECONFIG",
                        "TF_VAR_kube_config=$KUBECONFIG",
                        "TF_VAR_ghcr_username=$GHCR_USERNAME",
                        "TF_VAR_ghcr_token=$GHCR_TOKEN"
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


        stage('Download Model Artifacts (MLflow)') {
            steps {
                sh '''
                echo "Downloading model from MLflow..."

                python -m venv .venv_mlflow
                . .venv_mlflow/bin/activate

                pip install --no-cache-dir mlflow boto3 psycopg2-binary

                rm -rf models
                mkdir -p models

                export MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}

                mlflow artifacts download \
                  --artifact-uri models:/${MODEL_NAME}/${MODEL_STAGE} \
                  --dst-path models

                echo "Validating artifacts..."

                test -d models/models/phobert
                test -d models/models/lgbm
                test -f models/models/metadata.yaml

                echo "Model download successful"
                '''
            }
        }

        stage('Build & Push Docker Image') {
            steps {
                script {
                    sh """
                    docker build -f docker/Dockerfile.backend \
                      -t ${FULL_IMAGE}:${BUILD_NUMBER} .
                    """

                    withDockerRegistry([credentialsId: DOCKER_ID]) {
                        sh """
                        docker push ${FULL_IMAGE}:${BUILD_NUMBER}
                        docker tag ${FULL_IMAGE}:${BUILD_NUMBER} ${FULL_IMAGE}:latest
                        docker push ${FULL_IMAGE}:latest
                        """
                    }
                }
            }
        }

        stage('Manual Approval') {
            steps {
                input message: "Approve deployment to production?"
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([
                    string(credentialsId: HF_TOKEN_ID, variable: 'HF_TOKEN'),
                    file(credentialsId: KUBE_ID, variable: 'KUBECONFIG_FILE')
                ]) {
                    withEnv(["KUBECONFIG=${KUBECONFIG_FILE}"]) {
                        sh """
                        helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                          --namespace ${K8S_NAMESPACE} \
                          --create-namespace \
                          --set image.repository=${FULL_IMAGE} \
                          --set image.tag=${BUILD_NUMBER} \
                          --set secrets.hfToken=${HF_TOKEN} \
                          --wait --timeout 5m

                        kubectl rollout status deployment/${HELM_RELEASE} -n ${K8S_NAMESPACE}
                        kubectl get pods -n ${K8S_NAMESPACE}
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline completed successfully!"
        }
        failure {
            echo "Pipeline failed!"
        }
        always {
            cleanWs()
        }
    }
}