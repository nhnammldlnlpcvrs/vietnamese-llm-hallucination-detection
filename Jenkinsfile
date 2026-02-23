pipeline {
    agent any

    environment {
        KUBE_ID = 'kubeconfig-minikube'
        GHCR_ID = 'ghcr-credentials'
        HF_TOKEN_ID = 'hf-token'
        MLFLOW_ID = 'mlflow-credentials'
        MINIO_ID = 'minio-credentials'

        REGISTRY = 'ghcr.io'
        DOCKER_REGISTRY_USER = 'nhnammldlnlpcvrs'
        DOCKER_IMAGE_NAME = 'hallucination-backend'
        FULL_IMAGE = "${REGISTRY}/${DOCKER_REGISTRY_USER}/${DOCKER_IMAGE_NAME}"

        K8S_NAMESPACE = 'hallucination-prod'
        HELM_RELEASE = 'hallucination-backend'
        HELM_CHART_PATH = './kubernetes/charts/hallucination-backend'
        HELM_VALUES = './kubernetes/values/backend-prod.yaml'

        MLFLOW_TRACKING_URI = 'http://hallucination-mlflow:5000'
        MLFLOW_S3_ENDPOINT = 'http://hallucination-minio:9000'
        MLFLOW_MODEL_NAME = 'vihallu-detector'
        MLFLOW_MODEL_ALIAS = 'production'

        COVERAGE_THRESHOLD = '80'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_SHA_SHORT = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()
                    echo "Git SHA: ${env.GIT_SHA_SHORT}"
                }
            }
        }

        stage('Unit Test & Coverage') {
            steps {
                sh '''
                    docker build -f docker/Dockerfile.ci -t hallucination-ci:${GIT_SHA_SHORT} .

                    # Run tests & copy coverage.xml OUT of container
                    CONTAINER_ID=$(docker create hallucination-ci:${GIT_SHA_SHORT} \
                        pytest tests/unit \
                            --cov=backend \
                            --cov-report=xml:/tmp/coverage.xml \
                            --cov-fail-under=${COVERAGE_THRESHOLD})

                    docker start -a $CONTAINER_ID
                    EXIT_CODE=$?

                    docker cp $CONTAINER_ID:/tmp/coverage.xml ./coverage.xml || true
                    docker rm $CONTAINER_ID

                    exit $EXIT_CODE
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Quality Gate') {
            steps {
                script {
                    def coverage = sh(
                        script: """python3 -c \"
                            import xml.etree.ElementTree as ET
                            tree = ET.parse('coverage.xml')
                            print(round(float(tree.getroot().attrib['line-rate']) * 100, 1))
                            \"""",
                        returnStdout: true
                    ).trim().toFloat()

                    echo "Coverage: ${coverage}%  (threshold: ${COVERAGE_THRESHOLD}%)"

                    if (coverage < COVERAGE_THRESHOLD.toInteger()) {
                        error("Coverage ${coverage}% is below threshold ${COVERAGE_THRESHOLD}%")
                    }
                }
            }
        }

        stage('Provision Infra') {
            when {
                expression { params.PROVISION == true }
            }
            steps {
                withCredentials([
                    file(credentialsId: KUBE_ID, variable: 'KUBECONFIG'),
                    usernamePassword(
                        credentialsId: GHCR_ID,
                        usernameVariable: 'GHCR_USERNAME',
                        passwordVariable: 'GHCR_TOKEN'
                    )
                ]) {
                    withEnv([
                        "ANSIBLE_K8S_AUTH_KUBECONFIG=${KUBECONFIG}",
                        "TF_VAR_ghcr_username=${GHCR_USERNAME}",
                        "TF_VAR_ghcr_token=${GHCR_TOKEN}"
                    ]) {
                        dir('iac/terraform') {
                            sh '''
                                terraform init
                                terraform apply -auto-approve
                            '''
                        }
                        dir('iac/ansible') {
                            sh '''
                                ansible-galaxy collection install kubernetes.core --force
                                ansible-playbook setup_k8s_stack.yaml \
                                    -i inventory.ini \
                                    --extra-vars "kubeconfig_path=${KUBECONFIG}" \
                                    --start-at-task "Apply KServe ClusterServingRuntime (MLflow)"
                            '''
                        }
                    }
                }
            }
        }

        stage('Pull Model Artifacts') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: MINIO_ID,
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        pip install --quiet mlflow boto3

                        export MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}
                        export MLFLOW_S3_ENDPOINT_URL=${MLFLOW_S3_ENDPOINT}
                        export MLFLOW_S3_IGNORE_TLS=true

                        python scripts/pull_model_from_registry.py

                        # Validate artifacts
                        test -f backend/model_store/model_manifest.json
                        echo "[OK] Model artifacts ready"
                        cat backend/model_store/model_manifest.json
                    '''
                }
            }
        }

        stage('Build & Push Image') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: GHCR_ID,
                        usernameVariable: 'GHCR_USERNAME',
                        passwordVariable: 'GHCR_TOKEN'
                    )
                ]) {
                    sh '''
                        echo "${GHCR_TOKEN}" | docker login ghcr.io \
                            -u "${GHCR_USERNAME}" --password-stdin

                        docker build \
                            -f docker/Dockerfile.backend \
                            -t ${FULL_IMAGE}:${GIT_SHA_SHORT} \
                            -t ${FULL_IMAGE}:latest \
                            --build-arg GIT_SHA=${GIT_SHA_SHORT} \
                            .

                        docker push ${FULL_IMAGE}:${GIT_SHA_SHORT}
                        docker push ${FULL_IMAGE}:latest

                        echo "[OK] Pushed ${FULL_IMAGE}:${GIT_SHA_SHORT}"
                    '''
                }
            }
        }

        stage('Resolve StorageUri') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: MINIO_ID,
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        export MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}
                        export MLFLOW_S3_ENDPOINT_URL=${MLFLOW_S3_ENDPOINT}
                        export MLFLOW_MODEL_NAME=${MLFLOW_MODEL_NAME}
                        export MLFLOW_MODEL_ALIAS=${MLFLOW_MODEL_ALIAS}

                        python scripts/resolve_storage_uri.py \
                            --update-yaml mlops/kserve/inference-service.yaml

                        echo "[OK] inference-service.yaml updated"
                        grep storageUri mlops/kserve/inference-service.yaml
                    '''
                }
            }
        }

        stage('Approval') {
            steps {
                input message: "Deploy ${FULL_IMAGE}:${GIT_SHA_SHORT} to production?",
                      ok: "Deploy"
            }
        }

        stage('Deploy Backend') {
            steps {
                withCredentials([
                    file(credentialsId: KUBE_ID, variable: 'KUBECONFIG')
                ]) {
                    withEnv(["KUBECONFIG=${KUBECONFIG}"]) {
                        sh '''
                            helm upgrade --install ${HELM_RELEASE} ${HELM_CHART_PATH} \
                                --namespace ${K8S_NAMESPACE} \
                                --create-namespace \
                                -f ${HELM_VALUES} \
                                --set image.tag=${GIT_SHA_SHORT} \
                                --set image.repository=${FULL_IMAGE} \
                                --wait --timeout=5m

                            kubectl rollout status deployment/${HELM_RELEASE} \
                                -n ${K8S_NAMESPACE} --timeout=5m
                        '''
                    }
                }
            }
        }

        stage('Deploy KServe') {
            steps {
                withCredentials([
                    file(credentialsId: KUBE_ID, variable: 'KUBECONFIG')
                ]) {
                    withEnv(["KUBECONFIG=${KUBECONFIG}"]) {
                        sh '''
                            kubectl apply -f mlops/kserve/inference-service.yaml

                            # Wait for InferenceService ready (up to 5 min)
                            kubectl wait inferenceservice/hallucination-detector \
                                -n ${K8S_NAMESPACE} \
                                --for=condition=Ready \
                                --timeout=300s || \
                            kubectl get inferenceservice -n ${K8S_NAMESPACE}
                        '''
                    }
                }
            }
        }

        stage('Smoke Test') {
            steps {
                withCredentials([
                    file(credentialsId: KUBE_ID, variable: 'KUBECONFIG')
                ]) {
                    withEnv(["KUBECONFIG=${KUBECONFIG}"]) {
                        sh '''
                            # Port-forward backend for smoke test
                            kubectl port-forward svc/${HELM_RELEASE} 18000:8000 \
                                -n ${K8S_NAMESPACE} &
                            PF_PID=$!
                            sleep 5

                            # Health check
                            curl -f http://localhost:18000/health || \
                                (kill $PF_PID && exit 1)

                            # Quick inference test
                            curl -f -X POST http://localhost:18000/predict \
                                -H "Content-Type: application/json" \
                                -d '{"text": "smoke test", "context": "test"}' || \
                                (kill $PF_PID && exit 1)

                            kill $PF_PID
                            echo "[OK] Smoke test passed"
                        '''
                    }
                }
            }
        }
    }

    parameters {
        booleanParam(
            name: 'PROVISION',
            defaultValue: false,
            description: 'Run Terraform + Ansible provisioning (only needed for fresh setup)'
        )
    }

    post {
        success {
            echo """
            Pipeline PASSED
            Image  : ${FULL_IMAGE}:${env.GIT_SHA_SHORT}
            Commit : ${env.GIT_SHA_SHORT}
            """
        }
        failure {
            echo "Pipeline FAILED at stage: ${env.STAGE_NAME}"
        }
        always {
            cleanWs()
            sh 'docker image prune -f || true'
        }
    }
}