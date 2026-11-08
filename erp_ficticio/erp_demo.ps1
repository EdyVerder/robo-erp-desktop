# ERP de demonstração em Windows Forms: tela de login, lançamento de títulos e menu Sistema > Sair.
# Os nomes dos controles (txtUsuario, btnSalvar...) viram o AutomationId que o robô usa para achar cada campo.
#   powershell -STA -ExecutionPolicy Bypass -File erp_ficticio\erp_demo.ps1
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$fornecedores = 1..25 | ForEach-Object { 'Fornecedor Demonstração {0:000}' -f $_ }
$centros = @('Obra Demonstração 01', 'Obra Demonstração 02', 'Obra Demonstração 03', 'Administrativo', 'Comercial')
$script:proximo = 1201
$script:lancados = New-Object 'System.Collections.Generic.HashSet[string]'
$fonte = New-Object System.Drawing.Font('Segoe UI', 10)
$roxo = [System.Drawing.Color]::FromArgb(59, 42, 143)

function Novo-Rotulo($form, $texto, $x, $y) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $texto; $l.Location = New-Object System.Drawing.Point($x, $y); $l.AutoSize = $true
    $form.Controls.Add($l)
}

function Novo-Campo($form, $nome, $x, $y, $largura, $lista) {
    $t = New-Object System.Windows.Forms.TextBox
    $t.Name = $nome; $t.Location = New-Object System.Drawing.Point($x, $y); $t.Width = $largura
    $t.AccessibleName = $nome
    if ($lista) {
        $fonteAuto = New-Object System.Windows.Forms.AutoCompleteStringCollection
        $fonteAuto.AddRange([string[]]$lista)
        $t.AutoCompleteCustomSource = $fonteAuto
        $t.AutoCompleteMode = 'SuggestAppend'; $t.AutoCompleteSource = 'CustomSource'
    }
    $form.Controls.Add($t)
    return $t
}

function Novo-Botao($form, $nome, $texto, $x, $y) {
    $b = New-Object System.Windows.Forms.Button
    $b.Name = $nome; $b.Text = $texto; $b.Location = New-Object System.Drawing.Point($x, $y)
    $b.Size = New-Object System.Drawing.Size(120, 34); $b.BackColor = $roxo; $b.ForeColor = 'White'; $b.FlatStyle = 'Flat'
    $form.Controls.Add($b)
    return $b
}

# ---------- Login ----------
$login = New-Object System.Windows.Forms.Form
$login.Text = 'ERP Demonstração - Entrar'; $login.Font = $fonte; $login.StartPosition = 'CenterScreen'
$login.ClientSize = New-Object System.Drawing.Size(360, 230); $login.FormBorderStyle = 'FixedDialog'; $login.MaximizeBox = $false
Novo-Rotulo $login 'Usuário' 30 24
$txtUsuario = Novo-Campo $login 'txtUsuario' 30 46 300 $null
Novo-Rotulo $login 'Senha' 30 82
$txtSenha = Novo-Campo $login 'txtSenha' 30 104 300 $null
$txtSenha.UseSystemPasswordChar = $true
$lblErro = New-Object System.Windows.Forms.Label
$lblErro.Name = 'lblErro'; $lblErro.ForeColor = 'Firebrick'; $lblErro.Location = New-Object System.Drawing.Point(30, 140); $lblErro.AutoSize = $true
$login.Controls.Add($lblErro)
$btnEntrar = Novo-Botao $login 'btnEntrar' 'Entrar' 210 172
$login.AcceptButton = $btnEntrar
$btnEntrar.Add_Click({
    if ($txtUsuario.Text -eq 'demo.usuario' -and $txtSenha.Text -eq 'demo-2026') {
        $login.DialogResult = 'OK'; $login.Close()
    } else {
        $lblErro.Text = 'Usuário ou senha inválidos.'
    }
})
if ($env:ERP_DEMO_MINIMIZADO -eq '1') { $login.WindowState = 'Minimized' }
if ($login.ShowDialog() -ne 'OK') { exit 1 }

# ---------- Tela principal ----------
$tela = New-Object System.Windows.Forms.Form
$tela.Text = 'ERP Demonstração'; $tela.Font = $fonte; $tela.StartPosition = 'CenterScreen'
$tela.ClientSize = New-Object System.Drawing.Size(620, 380); $tela.FormBorderStyle = 'FixedSingle'; $tela.MaximizeBox = $false
$menu = New-Object System.Windows.Forms.MenuStrip
$sistema = New-Object System.Windows.Forms.ToolStripMenuItem('Sistema')
$sair = New-Object System.Windows.Forms.ToolStripMenuItem('Sair')
$sair.Name = 'menuSair'
$sair.Add_Click({ $tela.Close() })
[void]$sistema.DropDownItems.Add($sair)
[void]$menu.Items.Add($sistema)
$tela.MainMenuStrip = $menu
$tela.Controls.Add($menu)

$titulo = New-Object System.Windows.Forms.Label
$titulo.Text = 'Lançamento de títulos a pagar'; $titulo.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 13)
$titulo.Location = New-Object System.Drawing.Point(30, 40); $titulo.AutoSize = $true
$tela.Controls.Add($titulo)
Novo-Rotulo $tela 'Fornecedor' 30 84
$txtFornecedor = Novo-Campo $tela 'txtFornecedor' 30 106 360 $fornecedores
Novo-Rotulo $tela 'Documento' 410 84
$txtDocumento = Novo-Campo $tela 'txtDocumento' 410 106 180 $null
Novo-Rotulo $tela 'Vencimento (dd/mm/aaaa)' 30 146
$txtVencimento = Novo-Campo $tela 'txtVencimento' 30 168 170 $null
Novo-Rotulo $tela 'Valor (R$)' 220 146
$txtValor = Novo-Campo $tela 'txtValor' 220 168 170 $null
Novo-Rotulo $tela 'Centro de custo' 30 208
$txtCentro = Novo-Campo $tela 'txtCentro' 30 230 360 $centros
$btnSalvar = Novo-Botao $tela 'btnSalvar' 'Salvar' 470 290
$lblSituacao = New-Object System.Windows.Forms.Label
$lblSituacao.Name = 'lblSituacao'; $lblSituacao.Location = New-Object System.Drawing.Point(30, 298); $lblSituacao.Size = New-Object System.Drawing.Size(420, 50)
$tela.Controls.Add($lblSituacao)

$ptbr = [System.Globalization.CultureInfo]::GetCultureInfo('pt-BR')
$btnSalvar.Add_Click({
    $data = [datetime]::MinValue; $valor = [decimal]0
    $chave = $txtFornecedor.Text + '|' + $txtDocumento.Text
    $erro = $null
    if ($fornecedores -notcontains $txtFornecedor.Text) { $erro = 'Fornecedor não cadastrado.' }
    elseif (-not $txtDocumento.Text.Trim()) { $erro = 'Informe o documento.' }
    elseif (-not [datetime]::TryParseExact($txtVencimento.Text, 'dd/MM/yyyy', $ptbr, 'None', [ref]$data)) { $erro = 'Vencimento inválido.' }
    elseif (-not [decimal]::TryParse($txtValor.Text, [System.Globalization.NumberStyles]::Number, $ptbr, [ref]$valor) -or $valor -le 0) { $erro = 'Valor inválido.' }
    elseif ($centros -notcontains $txtCentro.Text) { $erro = 'Centro de custo não cadastrado.' }
    elseif ($script:lancados.Contains($chave)) { $erro = 'Documento já lançado para este fornecedor.' }
    if ($erro) {
        $lblSituacao.ForeColor = 'Firebrick'; $lblSituacao.Text = 'Erro: ' + $erro
        return
    }
    [void]$script:lancados.Add($chave)
    $lblSituacao.ForeColor = 'SeaGreen'; $lblSituacao.Text = ('Título {0:000000} gravado.' -f $script:proximo)
    $script:proximo++
    foreach ($c in @($txtFornecedor, $txtDocumento, $txtVencimento, $txtValor, $txtCentro)) { $c.Clear() }
})
if ($env:ERP_DEMO_MINIMIZADO -eq '1') { $tela.WindowState = 'Minimized' }
[void]$tela.ShowDialog()
