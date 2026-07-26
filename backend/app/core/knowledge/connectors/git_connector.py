import logging
import os
import tempfile

from app.core.knowledge.connectors.base import BaseKnowledgeConnector, ConnectorConfig
from app.core.knowledge.connectors.registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class GitConnector(BaseKnowledgeConnector):
    connector_type = "git"

    def validate(self, config: ConnectorConfig) -> bool:
        return bool(config.uri)

    def sync(self, config: ConnectorConfig) -> list[tuple[str, dict]]:
        uri = config.uri
        branch = config.config.get("branch", "main")
        include_exts = config.config.get("include_extensions", [".md", ".py", ".js", ".ts", ".txt", ".rst"])
        max_file_size = config.config.get("max_file_size_kb", 100) * 1024

        if not uri:
            logger.error("Git connector missing uri for source %s", config.source_id)
            return []

        tmp_dir = None
        try:
            import git

            tmp_dir = tempfile.mkdtemp(prefix="scout_git_")
            logger.info("Cloning %s branch=%s into %s", uri, branch, tmp_dir)
            repo = git.Repo.clone_from(uri, tmp_dir, branch=branch, depth=1)

            chunks = []
            for root, _dirs, files in os.walk(tmp_dir):
                if ".git" in root:
                    continue
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in include_exts:
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        if os.path.getsize(fpath) > max_file_size:
                            continue
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                        rel_path = os.path.relpath(fpath, tmp_dir)
                        if content.strip():
                            chunks.append((content, {"file_path": rel_path, "extension": ext}))
                    except Exception:
                        continue

            return chunks
        except Exception as exc:
            logger.exception("Git connector sync failed for source %s: %s", config.source_id, exc)
            return []
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)


ConnectorRegistry.register("git", GitConnector)
