# Agent Memory System - 浜戠缁忛獙鍏变韩绯荤粺

璺?Agent 璁板繂鍏变韩绯荤粺锛屾敮鎸佸皢缁忛獙涓婁紶鍒颁簯绔?MinIO 瀛樺偍锛屽叾浠?Agent 鍙笅杞藉涔犮€?
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 绯荤粺鏋舵瀯

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?                    浜戠鏈嶅姟鍣?(218.201.18.133)                  鈹?鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?   鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?鈹? 鈹?  MinIO (S3)      鈹?   鈹?        MySQL                    鈹? 鈹?鈹? 鈹?  绔彛: 8010       鈹?   鈹?        绔彛: 8999               鈹? 鈹?鈹? 鈹?  Bucket: openclaw 鈹?   鈹?  鏁版嵁搴? agent_memory           鈹? 鈹?鈹? 鈹?  瀛樺偍 MD 鏂囦欢      鈹?   鈹?  瀛樺偍缁忛獙鍏冩暟鎹?                鈹? 鈹?鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?   鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?鈹?          鈫?                           鈫?                        鈹?鈹?          鈹?        鍏冩暟鎹?+ 鏂囦欢璺緞    鈹?                        鈹?鈹?          鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                        鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                              鈫?                    Agent 璇锋眰 (S3 API + MySQL)
```

## 蹇€熷畨瑁?
### 绗竴姝ワ細鏈嶅姟鍣ㄩ儴缃诧紙浜戠绠＄悊浜哄憳鎵ц锛屼竴娆℃€э級

```bash
# 杩炴帴鍒颁簯鏈嶅姟鍣?ssh root@218.201.18.133

# 閮ㄧ讲 MinIO锛堝鏋滃皻鏈儴缃诧級
docker run -d --name minio --restart=always \
  -p 8010:9000 -p 8080:9001 \
  -v /data/minio:/data \
  -e 'MINIO_ROOT_USER=admin' \
  -e 'MINIO_ROOT_PASSWORD=Minio12345678' \
  minio/minio:latest server /data --console-address ':9001'

# 鍒涘缓 bucket
docker run --rm --network host -v /tmp:/tmp minio/mc \
  sh -c 'mc alias set myminio http://127.0.0.1:8010 admin Minio12345678 && mc mb myminio/openclaw'
```

### 绗簩姝ワ細瀹㈡埛绔畨瑁咃紙姣忓彴 OpenClaw 鏈哄櫒鎵ц锛?
```bash
# 鍏嬮殕椤圭洰
git clone <浠撳簱鍦板潃> agent-memory-system
cd agent-memory-system

# Windows 瀹夎
install.bat

# Linux/macOS 瀹夎
chmod +x install.sh && ./install.sh
```

### 绗笁姝ワ細閰嶇疆

缂栬緫 `config.yaml`锛?
```yaml
# MinIO 浜戠瀛樺偍
minio:
  endpoint: "218.201.18.133:8010"
  access_key: "admin"
  secret_key: "Minio12345678"
  bucket: "openclaw"
  region: "cn-east-1"

# MySQL 鏁版嵁搴?database:
  type: mysql
  host: "218.201.18.133"
  port: 8999
  database: "agent_memory"
  user: "root1"
  password: "浣犵殑瀵嗙爜"
  charset: "utf8mb4"

source: "cli"
agent_id: null

search:
  default_limit: 10
  max_limit: 100

log_level: "INFO"
```

### 绗洓姝ワ細鍒濆鍖栨暟鎹簱

```bash
# 鍒涘缓鏁版嵁搴撹〃
mysql -h 218.201.18.133 -P 8999 -u root1 -p agent_memory < scripts/init_mysql.sql
mysql -h 218.201.18.133 -P 8999 -u root1 -p agent_memory < scripts/init_experiences.sql
```

## 浣跨敤鏂规硶

### 鏌ョ湅鐘舵€?```bash
python src/cli/memory_cli.py status
```

### 瀛樺偍鏈湴璁板繂锛堜笉涓婁紶锛?```bash
python src/cli/memory_cli.py store "杩欐槸涓€涓湰鍦拌蹇? --type general
```

### 鍒嗕韩缁忛獙鍒颁簯绔紙鐢ㄦ埛瑙﹀彂锛?```bash
python src/cli/memory_cli.py exp-create \
    --title "MinIO閮ㄧ讲鏈€浣冲疄璺? \
    --summary "S3鍏煎瀛樺偍锛孉gent鍙嬪ソ" \
    --tags minio,storage,s3 \
    --domain DEVOPS \
    --importance 8 \
    --content "# MinIO閮ㄧ讲缁忛獙

## 鐜
CentOS 7, Docker

## 姝ラ
1. 閮ㄧ讲 MinIO 瀹瑰櫒
2. 閰嶇疆 Nginx 鍙嶅悜浠ｇ悊
3. 鍒涘缓 bucket

## 娉ㄦ剰浜嬮」
绔彛闇€鍦ㄥ畨鍏ㄧ粍寮€鏀?
```

### 鏌ヨ浜戠缁忛獙
```bash
python src/cli/memory_cli.py cloud-query "MinIO閮ㄧ讲"
```

### 涓嬭浇骞跺涔犵粡楠?```bash
# 鑾峰彇缁忛獙璇︽儏锛堝寘鍚枃浠惰矾寰勶級
python src/cli/memory_cli.py exp-get EXP-DEVOPS-MINIO-0001

# 涓嬭浇 MD 鏂囦欢鍒版湰鍦?python src/cli/memory_cli.py exp-download EXP-DEVOPS-MINIO-0001 --output ./learned/
```

### 鍒楀嚭鎵€鏈変簯绔粡楠?```bash
python src/cli/memory_cli.py exp-list
```

## 缁忛獙浠ｇ爜瑙勫垯

姣忎釜缁忛獙鏈夊敮涓€浠ｇ爜锛屾牸寮忥細`EXP-{DOMAIN}-{TAG}-{SEQ:4}`

| 閮ㄥ垎 | 璇存槑 | 绀轰緥 |
|------|------|------|
| `EXP` | 鍥哄畾鍓嶇紑 | EXP |
| `{DOMAIN}` | 棰嗗煙 | BACKEND / DEVOPS / AI |
| `{TAG}` | 涓昏鏍囩 | MINIO / DOCKER / FASTAPI |
| `{SEQ:4}` | 搴忓彿 | 0001 |

### 棰嗗煙浠ｇ爜

| 浠ｇ爜 | 棰嗗煙 |
|------|------|
| `BACKEND` | 鍚庣 |
| `FRONTEND` | 鍓嶇 |
| `DEVOPS` | 杩愮淮 |
| `AI` | 浜哄伐鏅鸿兘 |
| `DATABASE` | 鏁版嵁搴?|
| `GENERAL` | 閫氱敤 |

## OpenClaw 瑙﹀彂璇?
| 鐢ㄦ埛杈撳叆 | OpenClaw 鍔ㄤ綔 |
|---------|--------------|
| `璁颁綇xxx` | 瀛樺偍鍒版湰鍦拌蹇?|
| `鍒嗕韩缁忛獙` | 鍒嗕韩缁忛獙鍒颁簯绔紙MinIO + MySQL锛?|
| `璋佹湁xxx缁忛獙` | 鏌ヨ浜戠缁忛獙 |
| `鍊熼壌浜戠缁忛獙` | 涓嬭浇骞跺涔犱簯绔粡楠?|

## 椤圭洰缁撴瀯

```
agent-memory-system/
鈹溾攢鈹€ src/
鈹?  鈹溾攢鈹€ core/                 # 鏍稿績妯″潡
鈹?  鈹?  鈹溾攢鈹€ config.py         # 閰嶇疆绠＄悊
鈹?  鈹?  鈹溾攢鈹€ models.py         # 鏁版嵁妯″瀷
鈹?  鈹?  鈹溾攢鈹€ database.py        # MySQL 杩炴帴
鈹?  鈹?  鈹溾攢鈹€ minio_client.py   # MinIO 瀹㈡埛绔?猸?鈹?  鈹?  鈹溾攢鈹€ file_storage.py   # 鏂囦欢瀛樺偍
鈹?  鈹?  鈹斺攢鈹€ search.py          # 鎼滅储
鈹?  鈹溾攢鈹€ cli/
鈹?  鈹?  鈹斺攢鈹€ memory_cli.py     # CLI 涓荤▼搴?鈹?  鈹斺攢鈹€ adapters/             # Agent 閫傞厤鍣?鈹?      鈹斺攢鈹€ openclaw/         # OpenClaw 涓撶敤
鈹溾攢鈹€ scripts/
鈹?  鈹溾攢鈹€ init_mysql.sql        # MySQL 鍒濆鍖?鈹?  鈹斺攢鈹€ init_experiences.sql  # 缁忛獙琛?鈹溾攢鈹€ skills/
鈹?  鈹斺攢鈹€ minio-storage/        # MinIO Skill 猸?鈹溾攢鈹€ config.yaml.example       # 閰嶇疆绀轰緥
鈹溾攢鈹€ install.bat / install.sh   # 瀹夎鑴氭湰
鈹斺攢鈹€ README.md
```

## 浜戠鏈嶅姟淇℃伅

### MinIO (S3 鍏煎瀛樺偍)
| 閰嶇疆椤?| 鍊?|
|--------|-----|
| **API 鍦板潃** | `http://218.201.18.133:8010` |
| **Console** | `http://218.201.18.133:8080` |
| **Bucket** | `openclaw` |
| **Access Key** | `admin` |
| **Secret Key** | `Minio12345678` |

### MySQL (鍏冩暟鎹?
| 閰嶇疆椤?| 鍊?|
|--------|-----|
| **鍦板潃** | `218.201.18.133:8999` |
| **鏁版嵁搴?* | `agent_memory` |
| **鐢ㄦ埛鍚?* | `root1` |

## 鏂囦欢鍛藉悕瑙勮寖

### 浜戠缁忛獙鏂囦欢
```
experiences/
鈹溾攢鈹€ 2026-04/
鈹?  鈹溾攢鈹€ EXP-DEVOPS-MINIO-0001.md
鈹?  鈹溾攢鈹€ EXP-BACKEND-FASTAPI-0001.md
鈹?  鈹斺攢鈹€ ...
```

### MD 鏂囦欢鏍煎紡
```markdown
# 缁忛獙鏍囬

## 鎽樿
涓€鍙ヨ瘽姒傛嫭

## 鏍囩
#tag1 #tag2

## 姝ｆ枃
璇︾粏缁忛獙鍐呭...

## 鍏冩暟鎹?*浠ｇ爜: EXP-DEVOPS-MINIO-0001*
*棰嗗煙: DEVOPS*
*閲嶈鎬? 8/10*
```

## 甯歌闂

### Q: MinIO 杩炴帴澶辫触
A: 妫€鏌ョ鍙?8010 鏄惁鍦ㄥ畨鍏ㄧ粍寮€鏀?
### Q: Console 鎵撲笉寮€
A: 妫€鏌ョ鍙?8080 鏄惁鍦ㄥ畨鍏ㄧ粍寮€鏀撅紝鎴栬闂?http://218.201.18.133:8080

### Q: 涓婁紶澶辫触
A: 纭 MinIO bucket `openclaw` 宸插垱寤猴紝鏉冮檺姝ｇ‘

### Q: 鏁版嵁搴撹繛鎺ュけ璐?A: 妫€鏌?MySQL 绔彛 8999 鏄惁寮€鏀撅紝瀵嗙爜鏄惁姝ｇ‘

