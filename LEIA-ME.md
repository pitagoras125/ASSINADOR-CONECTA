# Conecta PDF 1.0.0 — Avante Sistemas

Versão Windows baseada no Assinador Conecta 0.9.2 corrigido.

Novidades: nome e ícone; botões individuais no topo para juntar PDFs, separar páginas, converter imagens e digitalizar. As listas permitem reordenar antes de criar PDF. A data de nascimento recebe as barras automaticamente. A chancela admite sobreposição e mantém o desenho aprovado. As operações de organização preservam os originais; PDFs assinados são recusados na junção/separação para não apresentar uma cópia modificada como assinatura válida.

Digitalização no Windows: selecione um scanner WIA, a resolução e o formato antes de iniciar. Para PDFs separados, conclua cada documento depois de digitalizar suas páginas.

Atualizações: verificação ao abrir e a cada seis horas com o programa aberto. Download automático e instalação iniciada ao fechar o programa, sem solicitar confirmação. Configurações permite desativar e verificar manualmente. O programa não atualiza durante uma assinatura ou diálogo modal. Metadados devem ser assinados pelo responsável e o instalador precisa corresponder ao SHA-256. O primeiro instalador precisa ser instalado manualmente: a versão antiga não possui este atualizador.

O canal Windows usa desktop-update.json separado do APK. Este pacote de teste ainda não publica o canal. Nenhuma conta, caixa de entrada ou serviço Firebase foi acrescentado.

## Instalar
Execute Instalar_Conecta_PDF_1.0.0.exe. A identidade e a pasta de instalação anteriores são preservadas para atualização no mesmo local. O instalador é para Windows 64 bits; este build não possui assinatura Authenticode comercial. Não force a associação padrão de PDF: escolha Conecta PDF nos aplicativos padrão do Windows.

## Compilar a partir do código
Python 3.12 no Windows; execute GERAR_EXECUTAVEL.bat e compile instalador.iss com Inno Setup 6.

## Lançamentos futuros
Guarde a chave privada de assinatura de atualizações fora do repositório. CRIAR_MANIFESTO_ATUALIZACAO.py gera desktop-update.json assinado. Publique esse arquivo e o EXE autorizado no canal indicado em desktop_updates.py. Não publique a chave privada. A verificação é criptográfica mesmo sem Authenticode. Como o canal usa releases/latest, preserve os arquivos de atualização de ambos os produtos quando publicar uma nova versão mobile ou desktop.

Validação local: 40 testes aprovados; interface Qt executada em modo offscreen. Instalação, certificados do Windows e scanner exigem validação no Windows real.
