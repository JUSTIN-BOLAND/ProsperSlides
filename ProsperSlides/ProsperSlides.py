"""ProsperSlides.py

Utility for making/pushing weekly Prosper Market Show Sldies

Using: https://developers.google.com/slides API
-- python lib: https://developers.google.com/slides
"""

from datetime import datetime
from os import path, makedirs, access, W_OK#, R_OK

import ujson as json
import requests
from plumbum import cli, local

import Helpers as ps_helper
import Plotting as ps_plotting
#import prosper.common.prosper_logging as p_logging
#import prosper.common.prosper_config as p_config

HERE = path.abspath(path.dirname(__file__))
ME = __file__.replace('.py', '')
CONFIG_ABSPATH = path.join(HERE, 'ProsperSlides.cfg')
config = ps_helper.CONFIG
logger = ps_helper.DEFAULT_LOGGER

def path_platform(filepath):
    """figure out which imagehost/sharing platform is being used

    Args:
        filepath (str): path to dump directory

    Returns:
        (:obj:`Helpers.HostPlatform`): Enum of which platform is being used

    """
    host = ps_helper.HostPlatform.ERROR
    types_found = 0

    if 'dropbox' in str(filepath).lower():
        host = ps_helper.HostPlatform.DROPBOX
        types_found += 1
    elif 'google' in str(filepath).lower():
        host = ps_helper.HostPlatform.GOOGLE
        types_found += 1
    else:
        raise ps_helper.UnsupportedHost('Unable to resolve host in=' + str(filepath))

    if types_found != 1:
        raise ps_helper.ConfusingHosts('Multiple possible hosts identified in=' + str(filepath))

    return host

def load_graph_profile(profile_filepath):
    """load profile for making graphs"""
    try:
        with open(profile_filepath, 'r') as filehandle:
            graph_profile_obj = json.load(filehandle)
    except Exception as err_msg:
        logger.error(
            'EXCEPTION: Unable to load graph profile from file:' +
            '\n\profile_filepath{0}'.format(profile_filepath),
            exc_info=True
        )
        raise err_msg
    try:
        ps_helper.validate_json(
            graph_profile_obj,
            'graphlist_schema.json'
        )
    except Exception as err_msg:
        logger.error(
            'EXCEPTION: json file not validated' +
            '\n\tproject_filepath={0}'.format(profile_filepath) +
            '\n\tjson_schemafile={0}'.format('graphlist_schema.json'),
            exc_info=True
        )
        raise err_msg

    return graph_profile_obj

def generate_plots(
        plot_profiles,
        debug_output=False
    ):
    """using the plot profile, walk through and generate plots

    Args:
        plot_profile (:obj:`dict`): JSON serialized collection of plot profiles
        debug_output (bool): flag for progress bar vs log-to-screen
    Returns:
        (:obj:`list` str): collection of filepaths where plots should be (in order)

    """
    progress_bar = cli.progress.ProgressBase(
        length=len(plot_profiles['plots']),
        has_output=debug_output
    )
    plot_list = []
    for index, plot_profile in enumerate(plot_profiles['plots']):
        progress_bar.display()
        logger.info('--plotting: ' + plot_profile['filename'])

        index_str = '%03d' % index
        plot_filename = '{index}_{filename}_{template}.png'.format(
            index=index_str,
            filename=plot_profile['filename'],
            profile=plot_profile['template']
        )
        try:
            plot_path = ps_plotting.plot(
                plot_profile['template'],
                plot_filename,
                plot_profile['required_args'],
                logger=logger
            )
        except Exception as err_msg:
            logger.warning(
                'EXCEPTION: building plot failed' +
                '\n\tplot_filename={0}'.format(plot_filename) +
                '\n\tplot_profile={0}'.format(plot_profile['template']) +
                '\n\texception={0}'.format(repr(err_msg))
            )
            progress_bar.increment()
            continue    #continue building plots

        plot_list.append(plot_path)
        progress_bar.increment()
    progress_bar.done()

class ProsperSlides(cli.Application):
    """Plumbum CLI application to build EVE Prosper Market Show slidedeck"""
    _log_builder = ps_helper.build_logger('ProsperSlides')  #TODO: fix ME?
    debug = cli.Flag(
        ['d', '--debug'],
        help='Debug mode, send data to local files'
    )

    @cli.switch(
        ['-v', '--verbose'],
        help='enable verbose logging')
    def enable_verbose(self):
        """toggle verbose output"""

        self._log_builder.configure_debug_logger()
        ps_helper.LOGGER = self._log_builder.logger

    outfile = ps_helper.test_filepath(
        path.join(local.env.home, 'Dropbox', 'Prosper Shownotes', 'Plots')
    )
    platform = ps_helper.HostPlatform.ERROR
    @cli.switch(
        ['-o', '--output'],
        str,
        help='base path to write plots to'
    )
    def set_output_file(self, filepath=outfile):
        """test to make sure path is ok"""
        self.outfile = ps_helper.test_filepath(filepath)
        self.platform = path_platform(filepath)

    graph_profile = load_graph_profile(path.join(HERE, 'default_graphlist.json'))
    @cli.switch(
        ['-p', '--profile'],
        str,
        help='Profile to build plots from (.json)'
    )
    def load_profile(self, profile_filepath):
        """load profile for making graphs"""
        self.graph_profile = load_graph_profile(profile_filepath)

    def main(self):
        global logger
        logger = self._log_builder.logger
        ps_helper.LOGGER = logger #TODO: this seems sloppy?
        logger.debug('hello world')
        logger.debug(self.outfile)
        logger.debug(self.graph_profile)

if __name__ == '__main__':
    ProsperSlides.run()
