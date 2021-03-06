<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>

<?php slot::start('head') ?>
    <title>Crash Data for <?php out::H($product . " " . (isset($version) && !empty($version) ? $version : "")); ?></title>
<?php echo html::stylesheet(array(
		'css/daily.css',
	), array('screen', 'screen')); ?>
<?php slot::end() ?>


<?php

View::factory('common/dashboard_product', array(
        'url_base' => $url_base,
        'product'  => $product,
        'version'  => $version
        ))->render(TRUE);

echo html::script(array(
        'js/flot-0.7/jquery.flot.pack.js',
        'js/socorro/utils.js',
        'js/jquery/mustache.js',
        'js/socorro/homepage_tmpl.js',
        'js/socorro/dashboard_graph.js',
        'js/socorro/daily.js',
    ));
?>
