# -*- coding: utf-8 -*-
<%inherit file="layout.mako"/>

<h1>${equip.name}</h1>

<h2>Actions</h2>
<ul>
  <li>
% if equip.running:
<a href="${request.route_url('stop', equip=equip.name)}">Stop ${equip.name}</a>
% else:
<a href="${request.route_url('start', equip=equip.name)}">Start ${equip.name}</a>
% endif
  </li>
  <li><a href="${request.route_url('list')}">Back to equipment list</a></li>
</ul>

<h2>Information</h2>
<ul>
  <li><strong>status:</strong> ${status}</li>
</ul>

<h2>Messages</h2>
<div id="dt">
  <div id="containter">
    <div class="dt_jui">
      <table id="logs" cellspacing="0" cellpadding="0" border="0" class="display">
        <thead>
          <tr>
            <th style="width: 85px">Date</th>
            <th style="width: 100px">Time</th>
            <th style="width: 250px">Module</th>
            <th style="width: 50px">Level</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script src="${request.static_url('gdaisremote:static/datatables/js/jquery.js')}"></script>
<script src="${request.static_url('gdaisremote:static/datatables/js/jquery.dataTables.js')}"></script>
<script>
  $.fn.dataTableExt.oApi.fnReloadAjax = function ( oSettings, sNewSource, fnCallback, bStandingRedraw )
  {
    if ( typeof sNewSource != 'undefined' && sNewSource != null )
    {
      oSettings.sAjaxSource = sNewSource;
    }
    this.oApi._fnProcessingDisplay( oSettings, true );
    var that = this;
    var iStart = oSettings._iDisplayStart;
    
    oSettings.fnServerData( oSettings.sAjaxSource, [], function(json) {
      /* Clear the old information from the table */
      that.oApi._fnClearTable( oSettings );
      
      /* Got the data - add it to the table */
      for ( var i=0 ; i<json.aaData.length ; i++ )
      {
        that.oApi._fnAddData( oSettings, json.aaData[i] );
      }
      
      oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
      that.fnDraw( that );
      
      if ( typeof bStandingRedraw != 'undefined' && bStandingRedraw === true )
      {
        oSettings._iDisplayStart = iStart;
        that.fnDraw( false );
      }
      
      that.oApi._fnProcessingDisplay( oSettings, false );
      
      /* Callback user function - for event handlers etc */
      if ( typeof fnCallback == 'function' && fnCallback != null )
      {
        fnCallback( oSettings );
      }
    }, oSettings );
  }

  var oTable;
  $(document).ready(function() {
    oTable = $('#logs').dataTable( {
      "bAutoWidth": false,
      "bDeferRender": true,
      "bJQueryUI": true,
      "bProcessing": true,
      "bStateSave": true,
      "sAjaxSource": '/view_log/${equip.name}',
      "sPaginationType": "full_numbers"
    });

% if equip.running: # only when new info may be added
    setInterval(function() {
      oTable.fnReloadAjax();
    }, 3000);
% endif

  });
</script>

<hr />
<h2>Debug</h2>
<ul>
  <li><strong>equip file path:</strong> ${equip_path}</li>
</ul>

