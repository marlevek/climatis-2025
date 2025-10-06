<?php "declare(encoding='pt_BR.UTF-8')\n";

// Aqui simplesmente estou pegando os input do formulário via post
$para = "vendas@climatis.com.br";
$Assunto = "Cotação de Produto via Website";
$nome = $_POST['nome'];
$email = $_POST['email'];
$produtos = $_POST['produtos'];


//AQUI ENVIO O PRIMEIRO EMAIL PARA O DESTINATARIO
$corpo = "<strong>Cotação de Produto via Site</strong><br><br>";
$corpo .= "<strong>Nome: </strong>" . $nome;
$corpo .= "<br><strong>Email: </strong>" . $email;
$corpo .= "<br><strong>Produto: </strong>" . $produtos;


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
