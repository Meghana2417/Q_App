pipeline {
    agent any

    environment {
        DOCKER_CREDS = credentials('docker-hub')
    }

    stages {
        stage('Clone Repo') {
            steps {
                git branch: 'main', url: 'https://github.com/Meghana2417/Q_App.git'
            }
        }

        stage('Docker Build') {
            steps {
                sh "docker build --no-cache -t meghana1724/qapp:latest ."
            }
        }

        stage('Docker Login') {
            steps {
                sh 'echo "$DOCKER_CREDS_PSW" | docker login -u "$DOCKER_CREDS_USR" --password-stdin'
            }
        }

        stage('Docker Push') {
            steps {
                sh "docker push meghana1724/qapp:latest"
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                docker stop qapp || true
                docker rm qapp || true

                docker pull meghana1724/qapp:latest

                docker run -d --name qapp -p 8000:8000 meghana1724/qapp:latest
                '''
            }
        }
    }
}
