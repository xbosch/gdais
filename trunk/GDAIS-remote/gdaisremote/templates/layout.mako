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
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/pylons.css')}" type="text/css" media="screen" charset="utf-8" />
  <link rel="stylesheet" href="http://fonts.googleapis.com/css?family=Neuton|Nobile:regular,i,b,bi&amp;subset=latin" type="text/css" media="screen" charset="utf-8" />
  <!--[if lte IE 6]>
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/ie6.css')}" type="text/css" media="screen" charset="utf-8" />
  <![endif]-->
  <link rel="stylesheet" href="${request.static_url('gdaisremote:static/gdais.css')}" type="text/css" media="screen" charset="utf-8" />
</head>

<body>

  % if request.session.peek_flash():
    <div id="flash">
      <% flash = request.session.pop_flash() %>
      % for message in flash:
        ${message}<br>
      % endfor
    </div>
  % endif

  <div id="page">
    ${next.body()}
  </div>

</body>
</html>
