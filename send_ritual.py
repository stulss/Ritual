import argparse
import json
import os
import sys
import time
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not DISCORD_WEBHOOK_URL or not GEMINI_API_KEY:
  print("환경 변수(DISCORD_WEBHOOK_URL, GEMINI_API_KEY)가 설정되지 않았습니다.")
  sys.exit(1)

MORNING_PROMPT = """
당신은 부트캠프/개발 실습 과정에 참여 중인 학습자를 위한 '아침 리추얼' 도우미입니다.
매일 아침 동료들과 공유하고 본인의 학습 시스템에 입력할 수 있는 새로운 내용을 작성해주세요.
딱딱한 AI 말투나 보고서형 명사형 어미(~함, ~태도)를 절대 피하고, 사람이 실제로 동료와 마주보고 대화하듯 자연스럽고 따뜻한 구어체로 작성해주세요.

다음 4가지 섹션으로 작성해주세요:

### 1. 편안했던 장면 하나 떠올리기
다음 3가지 옵션별로 바로 복사해 쓸 수 있는 서로 다른 예시를 1개씩 작성:
- 옵션 A (나를 행복하게 하는 물건이나 장소): '장면과 오늘 가져오고 싶은 조건' 예시
- 옵션 B (나를 행복하게 하는 생각): '장면과 오늘 가져오고 싶은 조건' 예시
- 옵션 C (내가 편안해지는 상상): '장면과 오늘 가져오고 싶은 조건' 예시

### 2. 내 인생의 기억에서 강점(장점)과 가치 찾기
아래 4개 테마 중 골라 쓸 수 있도록 각각 [최근 나의 장점을 드러내는 일화], [내가 한 행동의 의미], [내가 육성해야 할 나의 강점]을 구체적으로 작성:
- 선택지 1: [집요함 / 문제 해결] 에러나 버그를 끝까지 파고든 기억
- 선택지 2: [소통 / 경청] 동료의 의견을 먼저 귀담아듣고 조율한 기억
- 선택지 3: [기록 / 공유] 팀의 시행착오를 줄여준 지식 공유의 기억
- 선택지 4: [도전 / 실행력] 새로운 낯선 기술에 주저 없이 먼저 부딪혀본 기억

### 3. 남에 대한 평가는 나에 대한 평가 (아침 동료 칭찬 문구 20개)
- 특정 동료 이름은 절대 넣지 마세요.
- 오후 마감/퇴근 분위기 내용(x), '아침 출근/등원, 이른 준비, 아침 스크럼/질문, 하루를 시작하는 태도, 긍정적인 에너지' 등 아침 상황에 맞추세요.
- 실제 동료에게 "아침에 ~해 주셔서 정말 든든했어요"처럼 말하는 자연스러운 구어체 대화 문장으로 1번부터 20번까지 번호를 매겨 작성하세요.

### 4. 내가 주인이 되는 긍정의 목표 (선택지 4개)
다음 4가지 상황별로 [오늘 쓸 나의 강점]과 [이 강점을 위해 실천할 작은 행동]을 각각 작성:
- 선택지 1: [질문과 협업]
- 선택지 2: [몰입과 집중]
- 선택지 3: [침착한 디버깅]
- 선택지 4: [기록과 정리]
"""

AFTERNOON_PROMPT = """
당신은 부트캠프/개발 실습 과정에 참여 중인 학습자를 위한 '오후 마무리 리추얼' 도우미입니다.
하루를 돌아보며 작성할 수 있는 따뜻하고 솔직한 새로운 회고 세트를 작성해주세요.
딱딱한 보고서 어투를 피하고, 동료와 실제로 편하게 대화하듯 자연스러운 구어체를 사용해주세요.

다음 3가지 섹션으로 작성해주세요:

### 1. 강점 행동 돌아보기
- 어떤 아침 목표든 다 어울리는 [했다], [일부 했다], [못 했다] 범용 세트:
  각 상태별로 [내가 나의 강점을 위해 노력하고 생각한 것 한 줄]과 [오늘의 나에게 한 마디]를 작성.
- 아침 4대 테마(질문/소통, 몰입/집중, 침착한 디버깅, 기록/정리) 각각에 맞춘 [했다] 한 줄 예시 4종.

### 2. 오늘 감사했던 일을 동료들과 나눕니다 (대화체 20개)
- 특정 동료 이름은 빼고, 입력창에 '동료이름 | 내용'으로 쓰거나 직접 말할 수 있는 대화체 문장.
- 오늘 하루 동안(오후 실습, 디버깅 도움, 개념 설명, 코드 리뷰, 간식 챙기기, 점심 수다, 멘탈 케어 등) 동료에게 진심으로 고마웠던 구체적인 말 20개를 1번부터 20번까지 번호 매겨 작성.

### 3. 오늘의 감사일기 카드 (8가지 예시)
- '오늘 있었던 일' 입력칸에 들어갈 구체적인 일화 예시 8개.
- 코딩/학습뿐만 아니라 [점심/식사], [간식/배려], [수다/리프레시], [스트레칭/건강], [격려/공감], [협업/도움] 등 소소하고 따뜻한 일상 내용을 골고루 포함.
"""


def generate_gemini_content(prompt):
  # gemini-3.8-flash 로 지정
  url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
  headers = {"Content-Type": "application/json"}
  payload = {
      "contents": [{"parts": [{"text": prompt}]}],
      "generationConfig": {"temperature": 0.85},
  }
  response = requests.post(url, headers=headers, json=payload, timeout=60)
  response.raise_for_status()
  data = response.json()
  return data["candidates"][0]["content"]["parts"][0]["text"]


def send_to_discord(title, text):
  chunks = []
  current_chunk = f"## 📢 {title}\n\n"

  for line in text.split("\n"):
    if len(current_chunk) + len(line) + 2 > 1850:
      chunks.append(current_chunk)
      current_chunk = line + "\n"
    else:
      current_chunk += line + "\n"
  if current_chunk.strip():
    chunks.append(current_chunk)

  for chunk in chunks:
    res = requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk.strip()})
    if res.status_code not in (200, 204):
      print(f"디스코드 전송 오류 ({res.status_code}): {res.text}")
    time.sleep(1)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--mode",
      choices=["morning", "afternoon"],
      default="morning",
      help="실행 모드 (morning / afternoon)",
  )
  args = parser.parse_args()

  if args.mode == "morning":
    title = "🌅 [오전 9:00] 오늘의 아침 준비 리추얼 템플릿"
    prompt = MORNING_PROMPT
  else:
    title = "🌇 [오후 4:30] 오늘의 마무리 리추얼 템플릿"
    prompt = AFTERNOON_PROMPT

  print(f"{args.mode} 모드로 템플릿 생성을 시작합니다...")
  result_text = generate_gemini_content(prompt)
  print("디스코드로 전송합니다...")
  send_to_discord(title, result_text)
  print("전송 완료!")
