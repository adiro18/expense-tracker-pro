# Jenkins for Spendwise

## 1. Build and run

```bash
docker build -t spendwise-jenkins ./jenkins

docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --group-add 0 \
  spendwise-jenkins
```

* **Windows (Docker Desktop, Git Bash):** use a double slash so MSYS doesn't rewrite the path:
  `-v //var/run/docker.sock:/var/run/docker.sock`
  (PowerShell: `-v /var/run/docker.sock:/var/run/docker.sock` works as-is.)
* `--group-add 0` - inside the container the Docker Desktop socket is owned by `root:root`
  (mode 660). Adding the `jenkins` user to group 0 lets it use the socket without running Jenkins as root.
  On a Linux host use `--group-add $(stat -c %g /var/run/docker.sock)` instead.

Check that Docker works from inside Jenkins:

```bash
docker exec jenkins docker version --format '{{.Server.Version}}'
```

## 2. Unlock Jenkins

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open http://localhost:8080, paste the password, choose **Install suggested plugins**
(the plugins the pipeline needs - Pipeline, Git, Docker Pipeline, Credentials Binding,
Workspace Cleanup, Coverage - are already baked into the image), and create the admin user.

## 3. Docker Hub credentials

*Manage Jenkins → Credentials → System → Global credentials → Add Credentials*

| Field    | Value                                                      |
|----------|------------------------------------------------------------|
| Kind     | Username with password                                     |
| Username | your Docker Hub username (`adiro18`)                       |
| Password | a Docker Hub **access token** (hub.docker.com → Account settings → Personal access tokens, Read & Write) |
| ID       | `dockerhub-creds`  (must match the Jenkinsfile)            |

## 4. Create the pipeline job

*New Item → `spendwise` → Pipeline → OK*

* Definition: **Pipeline script from SCM**
* SCM: Git, Repository URL: `https://github.com/adiro18/expense-tracker-pro.git`
* Branch: `*/main`, Script Path: `Jenkinsfile`
* Save → **Build Now**

Stages: Checkout SCM → Test → Build image → Push image → Post actions.
The coverage report appears on the build page (Coverage plugin).

## Notes

* The image is built with `--platform linux/amd64` because EKS t3.micro nodes are x86_64.
  On an Apple Silicon Mac Docker Desktop emulates amd64, so the Build stage is slower there.
* If the build fails with `No such DSL method 'pipeline'`, the Pipeline plugin is missing.
* If a pipeline fails on line 1 with a strange character, the Jenkinsfile has a UTF-8 BOM
  (check with `head -c 3 Jenkinsfile | xxd` - it must start with `7069 70` = "pip").
