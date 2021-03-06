#!/usr/bin/env python

from __future__ import print_function
from util import logfmt, TemporaryDirectory, save_nifti, load_nifti
from plumbum import local, cli, FG
from plumbum.cmd import UKFTractography

from conversion import nhdr_write

import logging
logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format=logfmt(__file__))


# default UKFTractography parameters
ukfdefaults = ['--numTensor', 2, '--stoppingFA', 0.15, '--seedingThreshold', 0.18, '--Qm', 0.001, '--Ql', 70,
               '--Rs', 0.015, '--stepLength', 0.3, '--recordLength', 1.7, '--stoppingThreshold', 0.1,
               '--seedsPerVoxel', 10, '--recordTensors']


class App(cli.Application):
    """Convenient script to run UKFTractography"""

    dwi = cli.SwitchAttr('-i', cli.ExistingFile, help='DWI in nifti', mandatory= True)
    dwimask = cli.SwitchAttr('-m', cli.ExistingFile, help='mask of the DWI in nifti', mandatory=True)
    bvalFile = cli.SwitchAttr('--bvals', cli.ExistingFile, help='bval file for DWI', mandatory= True)
    bvecFile = cli.SwitchAttr('--bvecs', cli.ExistingFile, help='bvec file for DWI', mandatory= True)
    out = cli.SwitchAttr('-o', help='output tract file (.vtk)', mandatory= True)

    givenParams = cli.SwitchAttr('--params',
                help='provide comma separated UKF parameters: --arg1,val1,--arg2,val2,--arg3,val3 (no spaces)', default= ukfdefaults)

    def main(self):

        with TemporaryDirectory() as tmpdir:
            tmpdir = local.path(tmpdir)
            shortdwi = tmpdir / 'dwiShort.nii.gz'
            shortmask = tmpdir / 'maskShort.nii.gz'

            tmpdwi = tmpdir / 'dwi.nhdr'
            tmpdwimask = tmpdir / 'dwimask.nhdr'

            # TODO when UKFTractography supports float32, it should be removed
            # typecast to short
            short= load_nifti(self.dwi._path)
            save_nifti(shortdwi, short.get_data().astype('int16'), short.affine, short.header)

            short= load_nifti(self.dwimask._path)
            save_nifti(shortmask._path, short.get_data().astype('int16'), short.affine, short.header)

            # convert the dwi to NRRD
            nhdr_write(shortdwi._path, self.bvalFile._path, self.bvecFile._path, tmpdwi._path)

            # convert the mask to NRRD
            nhdr_write(shortmask._path, None, None, tmpdwimask._path)


            key_val_pair= self.givenParams.split(',')

            for i in range(0,len(ukfdefaults),2):

                try:
                    ind= key_val_pair.index(ukfdefaults[i])
                    ukfdefaults[i + 1] = key_val_pair[ind + 1]
                    key_val_pair[ind:ind+2]=[]
                except ValueError:
                    pass


            params = ['--dwiFile', tmpdwi, '--maskFile', tmpdwimask,
                      '--seedsFile', tmpdwimask, '--tracts',
                      self.out] + list(ukfdefaults) + key_val_pair


            logging.info('Peforming UKF tractography of {}'.format(tmpdwi))
            UKFTractography[params] & FG


if __name__ == '__main__':
    App.run()