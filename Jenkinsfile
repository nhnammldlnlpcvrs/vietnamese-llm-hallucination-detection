pipeline {
    agent any

    environment {
        KUBE_ID    = 'kubeconfig-gke'
        GHCR_ID    = 'ghcr-credentials'
        MINIO_ID   = 'minio-credentials'

        REGISTRY             = 'ghcr.io'
        DOCKER_REGISTRY_USER = 'nhnammldlnlpcvrs'
        DOCKER_IMAGE_NAME    = 'hallucination-backend'
        FULL_IMAGE           = "${REGISTRY}/${DOCKER_REGISTRY_USER}/${DOCKER_IMAGE_NAME}"

        K8S_NAMESPACE  = 'hallucination-prod'
        HELM_RELEASE   = 'hallucination-backend'
        HELM_CHART_PATH = './kubernetes/charts/hallucination-backend'
        HELM_VALUES    = './kubernetes/values/backend-prod.yaml'

        KSERVE_ISVC    = 'hallucination-detector'
        KSERVE_MANIFEST = './mlops/kserve/inference-service.yaml'
        GCS_MODEL_URI  = 'gs://vihallu-models/hallucination-detector/model'
        INGRESS_IP     = '136.110.57.217'

        MLFLOW_TRACKING_URI = 'http://localhost:5000'
        MLFLOW_S3_ENDPOINT  = 'http://localhost:9000'
        MLFLOW_MODEL_NAME   = 'vihallu-detector'
        MLFLOW_MODEL_ALIAS  = 'production'

        COVERAGE_THRESHOLD = '80'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    parameters {
        booleanParam(
            name: 'PROVISION',
            defaultValue: false,
            description: 'Run Terraform + Ansible provisioning (only for fresh setup)'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: 'Skip unit tests (emergency deploy only)'
        )
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
            when {
                expression { !params.SKIP_TESTS }
            }
            steps {
                sh '''
                    docker build -f docker/Dockerfile.ci \
                        -t hallucination-ci:${GIT_SHA_SHORT} .

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
            when {
                expression { !params.SKIP_TESTS }
            }
            steps {
                script {
                    def coverage = sh(
                        script: 'python3 -c "import xml.etree.ElementTree as ET; tree = ET.parse(\'coverage.xml\'); print(round(float(tree.getroot().attrib[\'line-rate\']) * 100, 1))"',
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
                        "USE_GKE_GCLOUD_AUTH_PLUGIN=True",
                        "TF_VAR_ghcr_username=${GHCR_USERNAME}",
                        "TF_VAR_ghcr_token=${GHCR_TOKEN}"
                    ]) {
                        dir('iac/terraform/gke') {
                            sh 'terraform init && terraform apply -auto-approve'
                        }
                        dir('iac/ansible') {
                            sh '''
                                KUBECONFIG=${KUBECONFIG} \
                                USE_GKE_GCLOUD_AUTH_PLUGIN=True \
                                ansible-playbook setup_gke_stack.yaml -v
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
                        export MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}
                        export MLFLOW_S3_ENDPOINT_URL=${MLFLOW_S3_ENDPOINT}
                        export MLFLOW_S3_IGNORE_TLS=true

                        pip install --quiet --break-system-packages mlflow boto3

                        python3 scripts/pull_model_from_registry.py

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
                sh """
                    sed -i 's|storageUri:.*|storageUri: "${GCS_MODEL_URI}"|' \
                        ${KSERVE_MANIFEST}

                    echo "[OK] storageUri → ${GCS_MODEL_URI}"
                    grep storageUri ${KSERVE_MANIFEST}
                """
            }
        }

        stage('Approval') {
            steps {
                input message: """
                        Deploy to GKE Production?
                        Image  : ${FULL_IMAGE}:${env.GIT_SHA_SHORT}
                        Model  : ${GCS_MODEL_URI}
                        """,
                      ok: "Deploy"
            }
        }

        stage('Deploy Backend') {
            steps {
                withCredentials([
                    file(credentialsId: KUBE_ID, variable: 'KUBECONFIG')
                ]) {
                    withEnv([
                        "KUBECONFIG=${KUBECONFIG}",
                        "USE_GKE_GCLOUD_AUTH_PLUGIN=True"
                    ]) {
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

                            echo "[OK] Backend deployed: ${FULL_IMAGE}:${GIT_SHA_SHORT}"
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
                    withEnv([
                        "KUBECONFIG=${KUBECONFIG}",
                        "USE_GKE_GCLOUD_AUTH_PLUGIN=True"
                    ]) {
                        sh '''
                            kubectl apply -f ${KSERVE_MANIFEST}

                            kubectl wait inferenceservice/${KSERVE_ISVC} \
                                -n ${K8S_NAMESPACE} \
                                --for=condition=Ready \
                                --timeout=300s || true

                            kubectl get inferenceservice -n ${K8S_NAMESPACE}
                            echo "[OK] KServe InferenceService deployed"
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
                    withEnv([
                        "KUBECONFIG=${KUBECONFIG}",
                        "USE_GKE_GCLOUD_AUTH_PLUGIN=True"
                    ]) {
                        sh """
                            ISVC_URL=http://${KSERVE_ISVC}.${K8S_NAMESPACE}.${INGRESS_IP}.nip.io

                            echo "Smoke testing: \$ISVC_URL"

                            # Health check
                            curl -f "\$ISVC_URL/v2/health/live" || \
                                (echo "[FAIL] Health check failed" && exit 1)

                            # Model ready
                            curl -f "\$ISVC_URL/v2/models/${KSERVE_ISVC}" || \
                                (echo "[FAIL] Model not ready" && exit 1)

                            echo "[OK] Smoke test passed"
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            echo """
                Pipeline PASSED
                Image  : ${FULL_IMAGE}:${env.GIT_SHA_SHORT}
                Model  : ${GCS_MODEL_URI}
                KServe : http://${KSERVE_ISVC}.${K8S_NAMESPACE}.${INGRESS_IP}.nip.io
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