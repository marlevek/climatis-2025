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
$assunto = $_POST['assunto'];
$mensagem = $_POST['msg'];

if (isset($_POST['g-recaptcha-response'])) {
  $captcha_data = $_POST['g-recaptcha-response'];
}

// Se nenhum valor foi recebido, o usuário não realizou o captcha
if (!$captcha_data) {
  echo "Por favor, confirme o captcha." . "<br>" . "<a href=https://www.climatis.com.br/contato.html#form>voltar</a>";
  exit;
}

$resposta = file_get_contents("https://www.google.com/recaptcha/api/siteverify?secret=6LclE6MZAAAAAOTZMMr8wlJ1g6OlJQatxk2u9Wuu=" . $captcha_data . "&remoteip=" . $_SERVER['REMOTE_ADDR']);

if ($resposta . success) {
  echo "Obrigado por deixar sua mensagem!";
} else {
  echo "Usuário mal intencionado detectado. A mensagem não foi enviada.";
  exit;
}

//AQUI ENVIO O PRIMEIRO EMAIL PARA O DESTINATARIO
$corpo = "<strong>Pedido de Orçamento pelo Site </strong><br><br>";
$corpo .= "<strong>Nome: </strong> $nome";
$corpo .= "<br><strong>Email: </strong> $email";
$corpo .= "<br><strong>Assunto: </strong> $assunto";
$corpo .= "<br><strong>Mensagem: </strong> $mensagem";


$headers  =  "Content-Type:text/html; charset=UTF-8\n";
$headers .= "From:  $email\n"; //Vai ser //mostrado que  o email partiu deste email e seguido do nome
$headers .= "X-Sender:  <br332.hostgator.com.br>\n"; //email do servidor //que enviou
$headers .= "X-Mailer: PHP  v" . phpversion() . "\n";
$headers .= "X-IP:  " . $_SERVER['REMOTE_ADDR'] . "\n";
$headers .= "Return-Path:  <orcamento@climatis.com.br>\n"; //caso a msg //seja respondida vai para  este email.
$headers .= "MIME-Version: 1.0\n";



mail($para, $Assunto, $corpo, $headers);



// verifica se está tudo ok com oa parametros acima, se nao, avisa do erro. Se sim, envia.
if ('mail') {
  $mgm = "E-MAIL ENVIADO COM SUCESSO! <br> O link será enviado para o e-mail fornecido no formulário";
  echo " <meta http-equiv='refresh' content='10;URL=contato.html'>";
} else {
  $mgm = "ERRO AO ENVIAR E-MAIL!";
  echo "";
}

echo "<script>location.href='resposta-contato.html'</script>";

if (preg_match("/bcc:|cc:|multipart|\[url|Content-Type:/i", implode($_POST))) {
  $spam = true;
}
