from dataclasses import dataclass

from sqlmodel import Session, func, select

from oceens.models import Summary

# `http_status` porte l'état de file et le résultat : 0 attend, 200 est fait,
# toute autre valeur est un échec (voir `oceens.models.Summary`).
_PENDING = 0
_DONE = 200

# Durée typique d'une synthèse : 20 s, mesurée sur `metadata_text` le
# 25 septembre 2026 (hypothèse B du Design Document, EPF-MDE/OceENS#110).
TYPICAL_JOB_SECONDS = 20


@dataclass(frozen=True)
class Progress:
    done: int
    total: int
    errors: int
    estimated_seconds_left: int


def progress(session: Session, survey_id: int) -> Progress:
    """Où en est ce sondage dans la file.

    L'estimation compte toutes les synthèses en attente de la file, de tous les
    sondages : un seul daemon les traite l'une après l'autre. Elle vaut 0 quand
    le sondage n'a plus rien en attente.
    """
    rows = session.exec(
        select(Summary.http_status, func.count())
        .where(Summary.survey_id == survey_id)
        .group_by(Summary.http_status)
    ).all()
    counts = dict(rows)
    pending = counts.get(_PENDING, 0)
    done = counts.get(_DONE, 0)
    total = sum(counts.values())
    errors = total - pending - done

    if pending == 0:
        return Progress(done, total, errors, 0)

    queue_length = session.exec(
        select(func.count()).where(Summary.http_status == _PENDING)
    ).one()
    return Progress(done, total, errors, queue_length * TYPICAL_JOB_SECONDS)
