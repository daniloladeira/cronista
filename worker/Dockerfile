# Worker de transcrição. Ver docs/12-transcricao.md §7-9, ADR-0002, ADR-0014.
#
# CUDA 12.9 + cuDNN 9: trocado em 2026-08-22, saindo de 12.1.0-cudnn8 (imagem
# marcada DEPRECATED/scheduled for deletion pelo registry da NVIDIA — não
# está mais na lista de tags suportadas em
# https://gitlab.com/nvidia/container-images/cuda/blob/master/doc/supported-tags.md).
# Motivo de ser cudnn9 e não outro cudnn8 mais novo: o pyproject.toml não
# fixa versão de ctranslate2 (vem transitivo de faster-whisper>=1.1), e a
# release instalada no build (4.8.1) exige cuDNN 9 — a partir da 4.5.0 do
# ctranslate2 o pacote não é mais compatível com cuDNN 8. A imagem cudnn8
# anterior funcionava mesmo assim (o caminho de inferência do Whisper usado
# aqui não parece bater no símbolo que muda de versão), mas isso não é
# garantia pra depender — cudnn9 é o par correto pra a lib que de fato está
# instalada. Validado nesta máquina antes da troca: rebuild completo do
# worker, `docker run --gpus all <imagem> nvidia-smi` reconhecendo a RTX
# 4060, e reprocessamento de uma reunião real de ~1h (a mesma do CT-16,
# docs/14-plano-de-testes.md) de ponta a ponta — 1079 segmentos persistidos,
# ~2min de transcrição, sem erro de cuDNN/CUDA. Se o build ou o `nvidia-smi`
# dentro do container falharem nesta máquina, é a primeira coisa a
# reconferir — versão de driver e de CUDA/cuDNN têm que casar (medido, não
# presumido, mesmo espírito de docs/12 §6).
FROM nvidia/cuda:12.9.2-cudnn-runtime-ubuntu22.04

# Sem isso, a instalação de dependência transitiva do tzdata abre um prompt
# interativo pedindo fuso horário e trava o build para sempre (não tem
# terminal do outro lado pra responder). Achado rodando o build de verdade,
# não adivinhado.
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo

# Python 3.13 (ADR-0008) não vem no Ubuntu 22.04 — via deadsnakes.
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.13 python3.13-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia só o que o build precisa antes do código, pra cache de camada
# sobreviver a mudança de código sem reinstalar dependência.
COPY pyproject.toml ./
COPY cronista/ ./cronista/

RUN python3.13 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instala o pacote inteiro (não só o necessário ao worker) por simplicidade —
# pyproject.toml ainda não separa dependências por processo. Se o build
# pesar ou quebrar por causa de dependência de cliente/API que não faz
# sentido aqui (ex.: soundcard exigindo lib de áudio do sistema), a correção
# é dividir pyproject.toml em grupos opcionais — adiado até isso acontecer
# de verdade, não decidido agora.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# `docker compose run --rm worker nvidia-smi` continua funcionando pra
# verificar a GPU, porque sobrescreve este CMD.
CMD ["python3.13", "-m", "cronista.worker.main"]
