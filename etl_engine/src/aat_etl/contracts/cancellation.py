"""A verified runtime cancellation token, distinct from pause or connection loss."""


class TransferCancelled(ValueError):pass


def check_cancelled(cancelled):
    if cancelled is not None and cancelled() is True:raise TransferCancelled('Execution was canceled; preserve verified commits and recovery evidence.')
