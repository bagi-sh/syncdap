Substituir a abordagem de corte via FFmpeg (*splitting*) pelo **re-download orquestrado** é a decisão arquitetural mais limpa para o `syncdap`. Cortar um áudio único localmente exigiria calcular timestamps acumulados, geraria *drift* (dessincronização) nos arquivos `.lrc` e ainda exigiria lidar com faixas ocultas ou pausas entre músicas. Com o re-download, cada faixa entra pelo fluxo nativo da sua CLI — ganhando metadados exatos, letras `.lrc` sincronizadas, gênero, `cover.jpg` otimizado para Rockbox e sanitização FAT32 sem precisar reescrever lógica de mídia.

Abaixo está o planejamento completo da feature (sugestão de flag: `--expand-albums` ou `--unbundle`), estruturado para substituir qualquer código de split anterior e maximizar o reuso do que já existe em `src/`.

---

## 1. Mapa de Reuso e Princípio DRY (O que NÃO reescrever)

O `syncdap` já possui uma camada compartilhada (`src/share/`) e módulos isolados (`src/modules/`) bem definidos. A nova feature deve atuar estritamente como um **orquestrador de alto nível**, delegando todo o trabalho pesado às funções já existentes:

| Componente Existente | O que já faz no `syncdap` | Como será reutilizado na nova feature |
| --- | --- | --- |
| **`src/share/audio.py`** | Varredura de biblioteca (`walk`) e leitura de tags/duração via Mutagen. | Usado na fase de auditoria para ler `audio.info.length` e tags (`ARTIST`, `ALBUM`, `TITLE`) e validar os novos arquivos baixados. |
| **`src/share/constants.py`** | Extensões suportadas (`FLAC`, `MP3`, etc.) e pastas ignoradas. | Define o formato alvo (mantendo o mesmo formato do arquivo falso) e ignora diretórios de sistema do DAP. |
| **`src/share/text.py`** | Sanitização de strings para FAT32, normalização e parsing de nomes. | Gera os nomes de arquivo padronizados (`01 - Titulo.ext`) dentro dos limites de caracteres do Rockbox/FAT32. |
| **`src/share/playlists.py`** | Busca de arquivos `.m3u8` e mapeamento/resolução de caminhos. | Localiza todas as playlists afetadas e converte caminhos absolutos/relativos corretamente. |
| **`src/modules/fallback.py`** | Download resiliente via `yt-dlp` com resgate de metadados. | Receberá o **filtro de duração** na origem e será chamado para baixar cada faixa individualmente. |
| **`src/patch/worker.py`** | Worker paralelo de download e validação de integridade do arquivo. | Reaproveita a lógica de execução em *threads* (`-t`) e verificação de arquivo não-corrompido. |
| **`src/modules/genres.py`** | Consulta de gêneros via iTunes, Deezer e MusicBrainz. | Chamado em lote apenas sobre a lista de novos arquivos gerados. |
| **`src/modules/lyrics.py`** | Busca e gravação de letras sincronizadas `.lrc`. | Chamado para baixar os `.lrc` individuais de cada faixa nova. |
| **`src/modules/rockbox_tags.py`** | Normalização de `ALBUMARTIST` e correção de tags vazias. | Garante que o álbum recém-baixado não fique fragmentado no banco de dados do Rockbox. |
| **`src/modules/covers.py`** | Extração de capa embutida para `cover.jpg` na pasta do álbum. | Extrai a capa de uma das faixas novas para `cover.jpg` e limpa as tags pesadas das demais. |

> **Regra de ouro:** Nenhuma função nova deve abrir arquivos `.m3u8` manualmente, chamar `mutagen` diretamente para varrer pastas ou implementar chamadas próprias à API do LRCLIB/MusicBrainz. Tudo isso já mora em `src/share/` e `src/modules/`.

---

## 2. Pré-requisito: Estancar o Problema na Origem (`src/modules/fallback.py`)

Antes de rodar o reparo nos arquivos antigos, o `fallback.py` precisa ser atualizado para que o próprio re-download não baixe o álbum inteiro novamente:

1. **Parâmetro de Duração Esperada:** A função de busca/download do `fallback.py` passa a aceitar `expected_duration_sec: float | None = None`.
2. **Filtro de Tolerância:** Ao inspecionar resultados do `yt-dlp` (`extract_info` sem download), descarta vídeos onde `abs(video_duration - expected_duration_sec) > 25` segundos.
3. **Negativação na Query e Prioridade `- Topic`:** Injeta `-"full album" -"álbum completo" -"discography"` na query e prioriza canais terminados em ` - Topic`.

---

## 3. Arquitetura da Nova Feature (`--expand-albums`)

### Onde os arquivos ficam

* **Remoção:** Excluir qualquer rascunho/função de corte por timestamps via `ffmpeg` que estava sendo desenvolvida.
* **Novo Módulo:** `src/modules/album_expander.py` (segue o padrão de `playlist_repair.py` e `dedup.py`).
* **Integração Bash:**
* `src/sh/cli.sh`: Adiciona a flag `--expand-albums` (e suporta `-d/--dry-run`, `-y/--yes`, `-r/--root-dir`, `-t/--threads`, `-F/--format`).
* `src/sh/orchestrator.sh`: Despacha a execução via `uv run python -m src.modules.album_expander ...`.



---

## 4. Fluxo Lógico Completo (5 Etapas)

```
[1. Auditoria (src/share/audio.py)]
       │  Compara duração física (Mutagen) vs. duração esperada da faixa
       ▼
[2. Resolução da Tracklist Oficial]
       │  Busca faixas 1..N do álbum (Spotify / MusicBrainz)
       ▼
[3. Re-download & Enriquecimento (worker + fallback + modules)]
       │  Baixa cada faixa separada -> genres -> lyrics -> covers -> rockbox_tags
       ▼
[4. Patching 1-para-N nas Playlists (src/share/playlists.py)]
       │  Substitui a entrada do arquivo único pela lista ordenada [faixa_1..faixa_N]
       ▼
[5. Validação e Limpeza Segura]
          Apaga o arquivo-álbum antigo (e seu .lrc) somente se o download teve sucesso

```

### Etapa 1: Detecção de Falsos Singulares (`scan_bundled_albums`)

1. Usa o iterador de arquivos de `src/share/audio.py` respeitando `--root-dir`.
2. Para cada faixa, obtém `actual_duration` (via Mutagen) e os metadados `artist`, `album` e `title`.
3. **Filtro rápido (evita chamadas desnecessárias de API):** Ignora arquivos com menos de `12 minutos` (720s) — a menos que `title.lower() == album.lower()` e o arquivo tenha mais de `8 minutos`.
4. Para os candidatos acima do limiar, consulta a duração esperada da faixa individual (via Spotify/MusicBrainz).
5. Se `actual_duration > expected_duration * 2.2`, classifica o arquivo como um `BundledAlbumCandidate` e guarda:
* `old_path`: Caminho do arquivo falso.
* `target_format`: Extensão atual do arquivo (ex: `.flac` ou `.mp3`), ou o formato forçado via `-F`.
* `artist` / `album`: Para buscar a *tracklist*.



### Etapa 2: Resolução da Tracklist Completa

1. Busca os metadados do álbum completo (Spotify API via `spotdl` ou MusicBrainz) usando `artist` + `album`.
2. Extrai a lista ordenada de faixas: `track_number`, `disc_number`, `title`, `artists`, `duration_sec`.
3. **Respeito ao `--dry-run` (`-d`):** Se o modo simulação estiver ativo, imprime no terminal o plano de ação (qual arquivo seria apagado, quais `N` faixas seriam baixadas e quais playlists `.m3u8` seriam alteradas) e encerra sem tocar no disco.

### Etapa 3: Re-download e Pipeline de Enriquecimento

Para cada faixa `1..N` do álbum (executando em paralelo com `ThreadPoolExecutor(max_workers=threads)`):

1. **Download:** Tenta baixar via `spotdl` (usando a URL/ID exato da faixa no Spotify). Se falhar, aciona `src/modules/fallback.py` passando `expected_duration_sec=track.duration_sec` e o formato `target_format`.
2. **Sanitização:** Garante que o arquivo salvo siga a árvore `Artist/Album/01 - Title.ext` sanitizada por `src/share/text.py`.
3. **Pós-processamento (Chamada direta aos módulos existentes):**
* Executa `rockbox_tags` nos novos arquivos (garante `TRACKNUMBER`, `TOTALTRACKS` e `ALBUMARTIST` consistentes).
* Executa `genres` nos novos arquivos.
* Executa `lyrics` nos novos arquivos (respeitando `--synced-only` se passado).
* Executa `covers` no diretório do álbum para extrair o `cover.jpg` e remover capas embutidas pesadas.



### Etapa 4: Patching `1-para-N` nas Playlists (`.m3u8`)

O `playlist_repair.py` atual resolve substituições `1-para-1` (quando um arquivo muda de nome ou extensão) e apaga links quebrados. Para não sujar a responsabilidade dele, criamos uma função específica de expansão `expand_playlist_entries(root_dir, migration_map)` apoiada nos helpers de `src/share/playlists.py`:

1. `migration_map` mapeia `{ old_path_resolvido: [new_track_01, new_track_02, ..., new_track_N] }`.
2. Usa `src/share/playlists.py` para listar todos os arquivos `.m3u8` da biblioteca.
3. Para cada playlist, percorre as linhas preservando comentários `#EXTM3U` / `#EXTINF`:
* Resolve o caminho da linha (relativo à pasta da playlist ou absoluto).
* Se bater com `old_path_resolvido`, substitui aquela **única linha** pelas **`N` linhas** das faixas novas na ordem exata do álbum (formatando cada novo caminho como relativo ou absoluto, espelhando o padrão da linha original).
* Evita duplicatas caso uma das faixas do álbum já existisse isoladamente naquela mesma playlist.


4. Salva a playlist de forma atômica (escreve em `.tmp` e faz `os.replace`).

### Etapa 5: Validação e Purga Segura (Proteção contra Perda de Dados)

Antes de remover o `old_path`:

1. Verifica via `src/share/audio.py` se os arquivos novos existem, têm tamanho `> 0 bytes` e duração válida.
2. **Critério de segurança:** Se **pelo menos 80%** das faixas do álbum foram baixadas e validadas com sucesso:
* Remove `old_path` do disco.
* Remove o arquivo de letra órfão correspondente (`old_path.with_suffix(".lrc")`), se existir.


3. Caso contrário (ex: queda de internet no meio do processo), mantém o `old_path` intacto e não aplica o *patch* nas playlists para aquele álbum, registrando um aviso no log.

---

## 5. Esqueleto Estrutural de Implementação (`src/modules/album_expander.py`)

Abaixo está a estrutura de como o código deve ser organizado para compor os módulos existentes sem duplicação:

```python
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from src.modules import covers, fallback, genres, lyrics, rockbox_tags
from src.share import audio, constants, playlists, text


@dataclass
class TrackSpec:
    number: int
    title: str
    artist: str
    album: str
    album_artist: str
    duration_sec: float
    spotify_url: str | None = None


@dataclass
class BundledCandidate:
    old_path: Path
    actual_duration: float
    expected_duration: float
    artist: str
    album: str
    fmt: str


def find_bundled_albums(root_dir: Path) -> list[BundledCandidate]:
    """Reutiliza src.share.audio para varrer a biblioteca e identificar

    arquivos cuja duração física excede drasticamente a faixa isolada.
    """
    candidates = []
    for file_path in audio.iter_audio_files(
        root_dir
    ):  # Função existente em share/audio.py
        meta = audio.read_metadata(file_path)
        if not meta or meta.duration < 480:  # Ignora faixas < 8 min
            continue

        expected_sec = fetch_expected_track_duration(meta.artist, meta.title)
        if expected_sec and meta.duration > (expected_sec * 2.2):
            candidates.append(
                BundledCandidate(
                    old_path=file_path,
                    actual_duration=meta.duration,
                    expected_duration=expected_sec,
                    artist=meta.artist,
                    album=meta.album or meta.title,
                    fmt=file_path.suffix.lstrip(".").lower(),
                )
            )
    return candidates


def download_single_track(
    track: TrackSpec, target_dir: Path, fmt: str
) -> Path | None:
    """Delega o download ao spotDL/fallback.py com trava de duração

    e sanitiza o caminho de saída via src.share.text.
    """
    safe_filename = text.sanitize_fat32(f"{track.number:02d} - {track.title}")
    out_path = target_dir / f"{safe_filename}.{fmt}"

    # 1. Tenta spotDL se houver URL; se falhar, aciona fallback com duração exata
    success = fallback.rescue_track(
        query=f"{track.artist} - {track.title}",
        output_path=out_path,
        audio_format=fmt,
        expected_duration=track.duration_sec,  # Filtro anti-álbum-completo
    )

    if success and audio.is_valid_audio(out_path):
        return out_path
    return None


def process_candidate(
    candidate: BundledCandidate, threads: int, dry_run: bool
) -> tuple[Path, list[Path]] | None:
    tracks = fetch_official_tracklist(candidate.artist, candidate.album)
    if not tracks:
        return None

    target_dir = candidate.old_path.parent
    if dry_run:
        # Apenas exibe o plano de substituição
        return (candidate.old_path, [])

    downloaded: list[Path] = []
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = [
            pool.submit(download_single_track, t, target_dir, candidate.fmt)
            for t in tracks
        ]
        for f in futures:
            res = f.result()
            if res:
                downloaded.append(res)

    # Trava de segurança: só substitui se >= 80% do álbum foi recuperado
    if len(downloaded) < max(1, int(len(tracks) * 0.8)):
        return None

    # Reutiliza pipeline de enriquecimento existente apenas nos arquivos novos
    rockbox_tags.normalize_files(downloaded)
    genres.enrich_files(downloaded)
    lyrics.fetch_for_files(downloaded)
    covers.extract_directory_cover(target_dir)

    return (candidate.old_path, sorted(downloaded))

```

### Integração no `src/sh/orchestrator.sh`

No `orchestrator.sh`, basta adicionar o bloco de despacho seguindo exatamente o mesmo padrão de `--repair-playlists` ou `--dedup`:

```bash
if [[ "$ACTION" == "expand-albums" ]]; then
    uv run python -m src.modules.album_expander \
        --root-dir "$ROOT_DIR" \
        --threads "$THREADS" \
        ${DRY_RUN:+--dry-run} \
        ${AUTO_YES:+--yes} \
        ${FORMAT:+--format "$FORMAT"}
    exit $?
fi

```

Quer que eu escreva o código completo e funcional do filtro de duração para o `src/modules/fallback.py` junto com o módulo `src/modules/album_expander.py`?
