# -*- coding: utf-8 -*-
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <meta charset="utf-8">
  <title>GDAIS remote control</title>
  <meta name="author" content="Pau Haro">
  <meta name="keywords" content="python web application" />
  <meta name="description" content="pyramid web application" />
  <link rel="shortcut icon" href="${request.static_url('gdaisremote:static/favicon.ico')}" />
  % if reload == True:
  <meta http-equiv="refresh" content="4" />
  % endif

  <!-- blueprint styles -->
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/css/blueprint/screen.css')}" type="text/css" media="screen, projection" />
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/css/blueprint/print.css')}" type="text/css" media="print" />
  <!--[if lt IE 8>
    <link rel="stylesheet" href="${request.static_url('gdaisremote:static/css/blueprint/ie.css')}" type="text/css" media="screen, projection" />
  <![endif]-->

  <!-- GDAIS styles -->
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/css/gdais.css')}" type="text/css" media="screen" charset="utf-8" />

  <!-- jQuery DataTables styles -->
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/datatables/css/datatables_page.css')}" type="text/css" media="screen" />
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/datatables/css/datatables_jui.css')}" type="text/css" media="screen" />
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/datatables/css/smoothness/jquery-ui-1.8.13.custom.css')}" type="text/css" media="screen" />

</head>

<body>

  % if request.session.peek_flash():
    <div id="flash">
      <% flash = request.session.pop_flash() %>
      % for message in flash:
      <div class="info">
        ${message}
      </div>
      % endfor
    </div>
  % endif

  <div id="page">
    ${next.body()}
  </div>

</body>
</html>
