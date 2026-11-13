# Jenkins controller that can run the Spendwise pipeline:
#   - docker CLI (+ buildx) talking to the host Docker through the mounted socket
#   - python3 + venv + pip for the Test stage
#   - the plugins the Jenkinsfile needs, pre-installed
FROM jenkins/jenkins:lts

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg python3 python3-venv python3-pip \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin \
    && rm -rf /var/lib/apt/lists/*
USER jenkins

# Pipeline, Git, Docker Pipeline, Credentials Binding, Workspace Cleanup, Coverage
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator git docker-workflow credentials-binding ws-cleanup coverage
