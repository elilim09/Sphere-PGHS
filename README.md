# Sphere-Pghs

# 기능

## 급식 이미지 조회
오늘 나올 급식의 이미지 조회가 가능합니다.

## 분실문 찾기
분실물을 찾을 수 있다.
---
# Docker
```
docker push hwanghj09/sphere-pghs:latest
```
이 프로젝트를 실행하기 위해선 `.env`파일이 필요합니다.

`.env` 파일 안에는
```
OPENAI_API_KEY = [openai api key]
```
이렇게 구성되어있어야합니다.

```
docker run --env-file .env -p 8000:8000 hwanghj09/sphere-pghs
```
위에서 만든 .env와 같은 디렉토리에서 이 명령어를 실행하면 서버가 실행됩니다.


