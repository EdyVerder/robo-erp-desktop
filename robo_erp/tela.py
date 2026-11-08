"""O robô na tela do ERP, pela automação de interface do Windows (pywinauto).

Cada campo é achado pelo AutomationId (o nome do controle) via UI Automation, nunca por coordenada de tela.
Para agir, o robô usa a mensagem do próprio Windows no controle achado (WM_SETTEXT, BM_CLICK): é instantâneo e
funciona com a janela ao fundo. No modo teclado, o texto é digitado tecla por tecla, como uma pessoa faria, porque
muitos ERPs desktop ignoram texto colado no campo de senha.
"""
import re
import subprocess
import time
from pathlib import Path

ERP = Path(__file__).resolve().parents[1] / "erp_ficticio" / "erp_demo.ps1"
BM_CLICK = 0x00F5


class ErroDeNegocio(Exception):
    """O ERP recusou o lançamento (fornecedor inexistente, duplicado...): não adianta repetir."""


class ErroDeTela(Exception):
    """A tela não respondeu como esperado (janela não abriu, campo sumiu)."""


def escapar_teclas(texto):
    """type_keys trata + ^ % ~ ( ) { } [ ] como comandos; entre chaves eles viram texto."""
    return re.sub(r"([+^%~(){}\[\]])", r"{\1}", texto)


class ErpDemo:
    def __init__(self, teclado=False, espera=10, espera_abrir=40):
        from pywinauto import Application
        from pywinauto.controls import win32_controls
        import win32api
        self._Application, self._win32, self._api = Application, win32_controls, win32api
        self.teclado = teclado
        self.espera = espera
        self.espera_abrir = espera_abrir
        self.app = None
        self.tela = None

    def abrir(self, comando=None):
        comando = comando or ["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File", str(ERP)]
        processo = subprocess.Popen(comando, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.app = self._Application(backend="uia").connect(process=processo.pid, timeout=self.espera)
        return self

    def _janela(self, titulo, espera=None):
        janela = self.app.window(title=titulo)
        # "ready" exige janela visível na tela; minimizada não conta, então basta existir e estar habilitada
        janela.wait("exists enabled", timeout=espera or self.espera)
        return janela

    def _controle(self, janela, auto_id, tipo):
        return janela.child_window(auto_id=auto_id, control_type=tipo).wrapper_object()

    def _digitar(self, campo, texto):
        edit = self._win32.EditWrapper(campo.handle)
        if self.teclado:
            edit.set_focus()
            edit.type_keys("{HOME}+{END}{DEL}" + escapar_teclas(texto), with_spaces=True, pause=0.03)
        else:
            edit.set_edit_text(texto)

    def _clicar(self, botao):
        self._api.PostMessage(botao.handle, BM_CLICK, 0, 0)

    def entrar(self, usuario, senha):
        login = self._janela("ERP Demonstração - Entrar", espera=self.espera_abrir)
        self._digitar(self._controle(login, "txtUsuario", "Edit"), usuario)
        self._digitar(self._controle(login, "txtSenha", "Edit"), senha)
        self._clicar(self._controle(login, "btnEntrar", "Button"))
        try:
            self.tela = self._janela("ERP Demonstração")
        except Exception:
            erro = login.child_window(auto_id="lblErro").window_text() if login.exists() else ""
            raise ErroDeTela(erro or "a tela principal não abriu depois do login")

    def lancar(self, titulo):
        """Preenche e salva um título; devolve o número gravado pelo ERP."""
        t = self.tela
        campos = {"txtFornecedor": titulo["fornecedor"], "txtDocumento": titulo["documento"],
                  "txtVencimento": titulo["vencimento"], "txtValor": titulo["valor"], "txtCentro": titulo["centro"]}
        for auto_id, valor in campos.items():
            self._digitar(self._controle(t, auto_id, "Edit"), valor)
        situacao = t.child_window(auto_id="lblSituacao")
        antes = situacao.window_text()
        self._clicar(self._controle(t, "btnSalvar", "Button"))
        inicio = time.monotonic()
        texto = antes
        while time.monotonic() - inicio < self.espera:
            texto = situacao.window_text()
            # mensagem nova, ou a mesma de antes repetida (duas recusas iguais seguidas) depois de um tempo
            if texto and (texto != antes or time.monotonic() - inicio > 1.5):
                break
            time.sleep(0.1)
        if texto.startswith("Erro:"):
            raise ErroDeNegocio(texto[5:].strip())
        achado = re.search(r"Título (\d+) gravado", texto)
        if not achado:
            raise ErroDeTela("o ERP não confirmou o lançamento")
        return achado.group(1)

    def foto(self, caminho):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        (self.tela or self.app.top_window()).capture_as_image().save(caminho)
        return caminho

    def sair(self):
        """Sai pelo menu, como uma pessoa; se o menu não responder, fecha a janela."""
        if not self.tela or not self.tela.exists():
            return
        try:
            self.tela.child_window(title="Sistema", control_type="MenuItem").expand()
            self.tela.child_window(title="Sair", control_type="MenuItem").invoke()
        except Exception:
            self.tela.close()
