pipeline {
  agent any
  environment {
    IMAGE_NAME = "adiro18/expense-tracker-pro"
    IMAGE_TAG  = "${env.BUILD_NUMBER}"
  }
  options {
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }
  stages {
    stage('Checkout SCM') { steps { checkout scm } }
    stage('Test') {
      steps {
        sh 'python3 -m venv venv'
        sh '. venv/bin/activate && pip install --timeout=180 --retries=10 -r requirements.txt'
        sh '. venv/bin/activate && pytest --cov=app --cov-report=xml --cov-fail-under=85'
      }
      post {
        always {
          // Publish coverage.xml here (post/always at pipeline level runs cleanWs first)
          script {
            try {
              recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'coverage.xml']])
            } catch (err) {
              echo "Coverage plugin not available - skipping coverage report (${err})"
            }
          }
        }
      }
    }
    // linux/amd64 because the EKS worker nodes (t3.micro) are x86_64, even if Jenkins runs on Apple Silicon
    stage('Build image') { steps { script { dockerImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}", "--platform linux/amd64 .") } } }
    stage('Push image') {
      steps {
        script {
          // Default registry ('' not 'https://registry.hub.docker.com') - explicit host broke via local mirror proxy
          docker.withRegistry('', 'dockerhub-creds') {
            dockerImage.push("${IMAGE_TAG}")
            dockerImage.push("latest")
          }
        }
      }
    }
  }
  post {
    always  { cleanWs() }
    success { echo "Published ${IMAGE_NAME}:${IMAGE_TAG}" }
    failure { echo "Build failed - image not published" }
  }
}
