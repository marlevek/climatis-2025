<?php "declare(encoding='pt_BR.UTF-8')\n";

// Recaptcha Google
if (isset($_POST['g-recaptcha-response'])) {
    $captcha_data = $_POST['g-recaptcha-response'];
  }
  
  // Se nenhum valor foi recebido, o usuário não realizou o captcha
  if (!$captcha_data) {
    echo '<h2 style="color:red;">Por favor, confirme o captcha.</h2>';
    exit;
  }
  $resposta = file_get_contents("https://www.google.com/recaptcha/api/siteverify?secret=6LeO4C8bAAAAAOMlGSWB5-CAUsQdhl3GSzTNxr_a&response=" . $captcha_data . "&remoteip=" . $_SERVER['REMOTE_ADDR']);
  
// Aqui simplesmente estou pegando os input do formulário via post
$para = "orcamento@climatis.com.br";
$Assunto = "Contato pelo Site";
$nome = $_POST['nome'];
$email = $_POST['email'];
$assunto = $_POST['asunto'];
$mensagem = $_POST['msg'];

//AQUI ENVIO O PRIMEIRO EMAIL PARA O DESTINATARIO
$corpo = "<strong>Pedido de Orçamento Manutenção Balcão Refrigerado </strong><br><br>";
$corpo .= "<strong>Nome: </strong>" . $nome;
$corpo .= "<br> <strong>Email: </strong>" . $email;
$corpo .= "<br> <strong>Assunto: </strong>" . $assunto;
$corpo .= "<br> <strong>Mensagem: </strong>" . $mensagem;

$headers = "From: $email" . "\r\n"; //Vai ser //mostrado que  o email partiu deste email e seguido do nome
$headers .= "X-Sender:  <br332.hostgator.com.br>\r\n"; //email do servidor //que enviou
$headers .= "MIME-Version: 1.0\r\n";
$headers .= "Content-Type: text/html; charset=UTF-8\r\n";
$headers .= "X=Mailer: PHP/" . phpversion();

// verifica se está tudo ok com oa parametros acima, se nao, avisa do erro. Se sim, envia.
if (mail($para, $Assunto, $corpo, $headers)) {
    echo "<script>location.href='resposta-contato.html'</script>";
} else {
    $mgm = "ERRO AO ENVIAR E-MAIL!";
    echo "<meta http-equiv='refresh' content='10;URL=contato.html'>";
}

if (preg_match("/bcc:|cc:|multipart|\[url|Content-Type:/i", implode($_POST))) {
    $spam = true;
}
