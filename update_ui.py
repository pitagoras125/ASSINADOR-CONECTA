from PySide6.QtCore import QThread,Signal,QTimer
from PySide6.QtWidgets import QMessageBox,QApplication
from desktop_updates import check_update,download_update,install_update

class UpdateJob(QThread):
    result=Signal(object);failed=Signal(str)
    def __init__(self,auto,parent=None):super().__init__(parent);self.auto=auto
    def run(self):
        try:
            payload=check_update();path=download_update(payload) if payload and self.auto else None
            self.result.emit((payload,path))
        except Exception as exc:self.failed.emit(str(exc) or 'Não foi possível verificar a assinatura da atualização.')

class Updates:
    def __init__(self,window):
        self.window=window;self.worker=None;self.pending=None
        self.timer = QTimer(window)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.check)
        self.timer.start(7000)
        self.close_requested = False
    def check(self,manual=False):
        if self.worker and self.worker.isRunning():return
        if self.pending:
            self.offer()
            return
        if self.window.busy() or QApplication.activeModalWidget() or self.window.dialog.isVisible():
            self.timer.start(60000)
            return
        if not manual and not self.window.settings.value('automatic_updates',True,type=bool):
            self.timer.start(60000)
            return
        self.worker=UpdateJob(True,self.window)
        self.worker.result.connect(lambda result:self.ready(result,manual));self.worker.failed.connect(lambda msg:self.failed(msg,manual))
        self.worker.finished.connect(self.finished)
        self.worker.start()
    def finished(self):
        if self.close_requested:
            self.close_requested = False
            QTimer.singleShot(0, self.window.close)

    def failed(self, message, manual):
        self.timer.start(5 * 60 * 1000)
        if manual:
            QMessageBox.warning(self.window, 'Atualizações', message)

    def ready(self,result,manual):
        self.timer.start(6 * 60 * 60 * 1000)
        payload,path=result
        if not payload:
            if manual:QMessageBox.information(self.window,'Atualizações','Nenhuma versão mais recente foi disponibilizada no canal Windows.')
            return
        self.pending=(payload,path)
        self.offer()
    def offer(self):
        # Atualização já validada e baixada: instalar quando o usuário encerrar o app.
        # Não interromper assinatura, edição ou trabalho em andamento.
        if not self.pending:
            return
        self.window.statusBar().showMessage(
            f"Conecta PDF {self.pending[0]['version']} baixado. Será instalado ao fechar o programa.",
            15000,
        )

    def install_on_exit(self):
        if not self.pending:
            return True
        payload, path = self.pending
        try:
            install_update(path, payload)
            self.pending = None
            return True
        except Exception as exc:
            QMessageBox.warning(self.window, 'Atualização',
                'Não foi possível iniciar a atualização automática.\n' + str(exc))
            return False
