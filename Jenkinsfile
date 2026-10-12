// Pipeline CRUD Mahasiswa untuk Jenkins yang berjalan di Windows + Docker Desktop.
// Kalau Jenkins-mu berjalan di Linux atau di dalam container, lihat catatan di README.

pipeline {
    agent any

    environment {
        APP_NAME  = 'crud-mahasiswa'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        APP_PORT  = '5000'
        // ID credential "Username with password": username Docker Hub + Access Token
        DOCKERHUB_CREDENTIALS = 'dockerhub-credentials'
    }

    options {
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                bat 'docker build -t %APP_NAME%:%IMAGE_TAG% -t %APP_NAME%:latest .'
            }
        }

        stage('Push ke Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDENTIALS,
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_TOKEN')]) {
                    bat 'echo %DH_TOKEN%| docker login -u %DH_USER% --password-stdin'
                    bat 'docker tag %APP_NAME%:%IMAGE_TAG% %DH_USER%/%APP_NAME%:%IMAGE_TAG%'
                    bat 'docker tag %APP_NAME%:%IMAGE_TAG% %DH_USER%/%APP_NAME%:latest'
                    bat 'docker push %DH_USER%/%APP_NAME%:%IMAGE_TAG%'
                    bat 'docker push %DH_USER%/%APP_NAME%:latest'
                }
            }
        }

        stage('Deploy (App + Database)') {
            steps {
                // Menjalankan container PostgreSQL + container app hasil build ini
                bat 'docker compose up -d --no-build --remove-orphans'
            }
        }

        stage('Verifikasi') {
            steps {
                // /health hanya menjawab 200 kalau app hidup DAN terhubung ke database
                retry(10) {
                    sleep(time: 3, unit: 'SECONDS')
                    bat 'curl -fsS http://localhost:%APP_PORT%/health'
                }
            }
        }
    }

    post {
        success {
            echo "Build #${env.BUILD_NUMBER} berhasil. Aplikasi berjalan di http://localhost:${env.APP_PORT}"
        }
        failure {
            // Tampilkan log container supaya penyebab gagal kelihatan di Console Output
            bat(script: 'docker compose logs --tail=50', returnStatus: true)
        }
        always {
            bat(script: 'docker logout', returnStatus: true)
        }
    }
}
