#!/usr/bin/env python

# Copyright 2019 Pascal Audet & Helen Janiszewski
#
# This file is part of OBStools.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Program atacr_download_data.py
------------------------------

Downloads four-component (H1, H2, Z and P), day-long seismograms 
to use in noise corrections of vertical
component data. Station selection is specified by a network and 
station code. The data base is provided in stations_db.pkl as a 
`StDb` dictionary.

Usage
-----

.. code-block::

    $ atacr_download_data.py -h
    Usage: atacr_download_data.py [options] <station database>

    Script used to download and pre-process up to four-component (H1, H2, Z and
    P), day-long seismograms to use in noise corrections of vertical component of
    OBS data. Data are requested from the internet using the client services
    framework for a given date range. The stations are processed one by one and
    the data are stored to disk.

    Options:
      -h, --help            show this help message and exit
      --keys=STKEYS         Specify a comma-separated list of station keys for
                            which to perform the analysis. These must be contained
                            within the station database. Partial keys will be used
                            to match against those in the dictionary. For
                            instance, providing IU will match with all stations in
                            the IU network. [Default processes all stations in the
                            database]
      -C CHANNELS, --channels=CHANNELS
                            Specify a comma-separated list of channels for which
                            to perform the transfer function analysis. Possible
                            options are H (for horizontal channels) or P (for
                            pressure channel). Specifying H allows for tilt
                            correction. Specifying P allows for compliance
                            correction. [Default looks for both horizontal and
                            pressure and allows for both tilt AND compliance
                            corrections]
      -O, --overwrite       Force the overwriting of pre-existing data. [Default
                            False]

      Server Settings:
        Settings associated with which datacenter to log into.

        -S SERVER, --Server=SERVER
                            Specify the server to connect to. Options include:
                            BGR, ETH, GEONET, GFZ, INGV, IPGP, IRIS, KOERI, LMU,
                            NCEDC, NEIP, NERIES, ODC, ORFEUS, RESIF, SCEDC, USGS,
                            USP. [Default IRIS]
        -U USERAUTH, --User-Auth=USERAUTH
                            Enter your IRIS Authentification Username and Password
                            (--User-Auth='username:authpassword') to access and
                            download restricted data. [Default no user and
                            password]

      Time Search Settings:
        Time settings associated with searching for day-long seismograms

        --start=STARTT      Specify a UTCDateTime compatible string representing
                            the start day for the data search. This will override
                            any station start times. [Default start date for each
                            station in database]
        --end=ENDT          Specify a UTCDateTime compatible string representing
                            the start time for the event search. This will
                            override any station end times [Default end date for
                            each station in database]

      Frequency Settings:
        Miscellaneous frequency settings

        --sampling-rate=NEW_SAMPLING_RATE
                            Specify new sampling rate (float, in Hz). [Default 5.]
        --pre-filt=PRE_FILT
                            Specify four comma-separated corner frequencies
                            (float, in Hz) for deconvolution pre-filter. [Default
                            0.001,0.005,45.,50.]

"""

# Import modules and functions
import numpy as np
import os.path
import pickle
import glob
import stdb
from obspy.clients.fdsn import Client
from obstools.atacr import utils, options

# Main function
def main():

    # Run Input Parser
    (opts, indb) = options.get_daylong_options()

    # Load Database
    db = stdb.io.load_db(fname=indb)

    # Construct station key loop
    allkeys = db.keys()
    sorted(allkeys)

    # Extract key subset
    if len(opts.stkeys) > 0:
        stkeys = []
        for skey in opts.stkeys:
            stkeys.extend([s for s in allkeys if skey in s])
    else:
        stkeys = db.keys()
        sorted(stkeys)

    # Loop over station keys
    for stkey in list(stkeys):

        # Extract station information from dictionary
        sta = db[stkey]

        # Define path to see if it exists
        datapath = 'DATA/' + stkey + '/'
        if not os.path.isdir(datapath): 
            print()
            print('Path to '+datapath+' doesn`t exist - creating it')
            os.makedirs(datapath)

        # Establish client
        if len(opts.UserAuth) == 0:
            client = Client(opts.Server)
        else:
            client = Client(opts.Server, user=opts.UserAuth[0], password=opts.UserAuth[1])

        # Get catalogue search start time
        if opts.startT is None:
            tstart = sta.startdate
        else:
            tstart = opts.startT

        # Get catalogue search end time
        if opts.endT is None:
            tend = sta.startdate
        else:
            tend = opts.endT

        if tstart > sta.enddate or tend < sta.startdate:
            continue

        # Temporary print locations
        tlocs = sta.location
        if len(tlocs) == 0: tlocs = ['']
        for il in range(0, len(tlocs)):
            if len(tlocs[il]) == 0: tlocs[il] = "--"
        sta.location = tlocs

        # Update Display
        print()
        print("|===============================================|")
        print("|===============================================|")
        print("|                   {0:>8s}                    |".format(sta.station))
        print("|===============================================|")
        print("|===============================================|")
        print("|  Station: {0:>2s}.{1:5s}                            |".format(sta.network, sta.station))
        print("|      Channel: {0:2s}; Locations: {1:15s}  |".format(sta.channel, ",".join(tlocs)))
        print("|      Lon: {0:7.2f}; Lat: {1:6.2f}                |".format(sta.longitude, sta.latitude))
        print("|      Start time: {0:19s}          |".format(sta.startdate.strftime("%Y-%m-%d")))
        print("|      End time:   {0:19s}          |".format(sta.enddate.strftime("%Y-%m-%d")))
        print("|-----------------------------------------------|")
        print("| Searching day-long files:                     |")
        print("|   Start: {0:19s}                  |".format(tstart.strftime("%Y-%m-%d")))
        print("|   End:   {0:19s}                  |".format(tend.strftime("%Y-%m-%d")))

        # Split into 24-hour long segments
        dt = 3600.*24.

        t1 = tstart
        t2 = tstart + dt

        while t2 <= tend:

            # Time stamp
            tstamp = str(t1.year).zfill(4)+'.'+str(t1.julday).zfill(3)+'.'

            print()
            print("***********************************************************")
            print("* Downloading day-long data for key "+stkey+" and day "+str(t1.year)+"."+str(t1.julday))
            print("*")
            print("* Channels selected: "+str(opts.channels)+' and vertical')

            # Define file names (to check if files already exist)
            file1 = datapath + tstamp + '.' + sta.channel + '1.SAC' # Horizontal 1 channel
            file2 = datapath + tstamp + '.' + sta.channel + '2.SAC' # Horizontal 2 channel
            fileZ = datapath + tstamp + '.' + sta.channel + 'Z.SAC' # Vertical channel
            fileP = datapath + tstamp + '.' + sta.channel + 'H.SAC' # Pressure channel

            if "P" not in opts.channels:

                # If data files exist, continue
                if glob.glob(fileZ) and glob.glob(file1) and glob.glob(file2): 
                    if not opts.ovr:
                        print("*   "+tstamp+"*SAC                                 ")
                        print("*   -> Files already exist, continuing            ")
                        t1 += dt
                        t2 += dt
                        continue

                channels = sta.channel.upper()+'1,'+sta.channel.upper()+'2,'+sta.channel.upper()+'Z'

                # Get waveforms from client
                try:
                    print("*   "+tstamp+"*SAC                                 ")
                    print("*   -> Downloading Seismic data... ")
                    sth = client.get_waveforms(network=sta.network, station=sta.station, location=sta.location[0], \
                            channel=channels, starttime=t1, endtime=t2, attach_response=True)
                    print("*      ...done")
                except:
                    print(" Error: Unable to download ?H? components - continuing")
                    t1 += dt
                    t2 += dt
                    continue

                # Make sure length is ok
                llZ = len(sth.select(component='Z')[0].data)
                ll1 = len(sth.select(component='1')[0].data)
                ll2 = len(sth.select(component='2')[0].data)

                if (llZ != ll1) or (llZ != ll2):
                    print(" Error: lengths not all the same - continuing")
                    t1 += dt
                    t2 += dt
                    continue

                ll = int(dt*sth[0].stats.sampling_rate)

                if np.abs(llZ - ll) > 1:
                    print(" Error: Time series too short - continuing")
                    print(np.abs(llZ - ll))
                    t1 += dt
                    t2 += dt
                    continue

            elif "H" not in opts.channels:

                # If data files exist, continue
                if glob.glob(fileZ) and glob.glob(fileP): 
                    if not opts.ovr:
                        print("*   "+tstamp+"*SAC                                 ")
                        print("*   -> Files already exist, continuing            ")
                        t1 += dt
                        t2 += dt
                        continue

                channels = sta.channel.upper() + 'Z'

                # Get waveforms from client
                try:
                    print("*   "+tstamp+"*SAC                                 ")
                    print("*   -> Downloading Seismic data... ")
                    sth = client.get_waveforms(network=sta.network, station=sta.station, location=sta.location[0], \
                            channel=channels, starttime=t1, endtime=t2, attach_response=True)
                    print("*      ...done")
                except:
                    print(" Error: Unable to download ?H? components - continuing")
                    t1 += dt
                    t2 += dt
                    continue
                try:
                    print("*   -> Downloading Pressure data...")
                    stp = client.get_waveforms(network=sta.network, station=sta.station, location=sta.location[0], \
                            channel='??H', starttime=t1, endtime=t2, attach_response=True)
                    print("*      ...done")
                except:
                    print(" Error: Unable to download ??H component - continuing")
                    t1 += dt
                    t2 += dt
                    continue

                # Make sure length is ok
                llZ = len(sth.select(component='Z')[0].data)
                llP = len(stp[0].data)

                if (llZ != llP):
                    print(" Error: lengths not all the same - continuing")
                    t1 += dt
                    t2 += dt
                    continue

                ll = int(dt*stp[0].stats.sampling_rate)

                if np.abs(llZ - ll) > 1:
                    print(" Error: Time series too short - continuing")
                    print(np.abs(llZ - ll))
                    t1 += dt
                    t2 += dt
                    continue

            else:

                # If data files exist, continue
                if glob.glob(fileZ) and glob.glob(file1) and glob.glob(file2) and glob.glob(fileP): 
                    if not opts.ovr:
                        print("*   "+tstamp+"*SAC                                 ")
                        print("*   -> Files already exist, continuing            ")
                        t1 += dt
                        t2 += dt
                        continue

                channels = sta.channel.upper()+'1,'+sta.channel.upper()+'2,'+sta.channel.upper()+'Z'

                # Get waveforms from client
                try:
                    print("*   "+tstamp+"*SAC                                 ")
                    print("*   -> Downloading Seismic data... ")
                    sth = client.get_waveforms(network=sta.network, station=sta.station, location=sta.location[0], \
                            channel=channels, starttime=t1, endtime=t2, attach_response=True)
                    print("*      ...done")
                except:
                    print(" Error: Unable to download ?H? components - continuing")
                    t1 += dt
                    t2 += dt
                    continue
                try:
                    print("*   -> Downloading Pressure data...")
                    stp = client.get_waveforms(network=sta.network, station=sta.station, location=sta.location[0], \
                            channel='??H', starttime=t1, endtime=t2, attach_response=True)
                    print("*      ...done")
                except:
                    print(" Error: Unable to download ??H component - continuing")
                    t1 += dt
                    t2 += dt
                    continue

                # Make sure length is ok
                llZ = len(sth.select(component='Z')[0].data)
                ll1 = len(sth.select(component='1')[0].data)
                ll2 = len(sth.select(component='2')[0].data)
                llP = len(stp[0].data)

                if (llZ != ll1) or (llZ != ll2) or (llZ != llP):
                    print(" Error: lengths not all the same - continuing")
                    t1 += dt
                    t2 += dt
                    continue

                ll = int(dt*sth[0].stats.sampling_rate)

                if np.abs(llZ - ll) > 1:
                    print(" Error: Time series too short - continuing")
                    print(np.abs(llZ - ll))
                    t1 += dt
                    t2 += dt
                    continue

            # Remove responses
            print("*   -> Removing responses - Seismic data")
            sth.remove_response(pre_filt=opts.pre_filt, output='DISP')
            if "P" in opts.channels:
                print("*   -> Removing responses - Pressure data")
                stp.remove_response(pre_filt=opts.pre_filt)

            # Detrend, filter - seismic data
            sth.detrend('demean')
            sth.detrend('linear')
            sth.filter('lowpass', freq=0.5*opts.new_sampling_rate, corners=2, zerophase=True)
            sth.resample(opts.new_sampling_rate)

            if "P" in opts.channels:
                # Detrend, filter - pressure data
                stp.detrend('demean')
                stp.detrend('linear')
                stp.filter('lowpass', freq=0.5*opts.new_sampling_rate, corners=2, zerophase=True)
                stp.resample(opts.new_sampling_rate)

            # Extract traces - Z
            trZ = sth.select(component='Z')[0]
            trZ = utils.update_stats(trZ, sta.latitude, sta.longitude, sta.elevation, 'Z')
            trZ.write(fileZ, format='sac')

            # Extract traces - H
            if "H" in opts.channels:
                tr1 = sth.select(component='1')[0]
                tr2 = sth.select(component='2')[0]
                tr1 = utils.update_stats(tr1, sta.latitude, sta.longitude, sta.elevation, '1')
                tr2 = utils.update_stats(tr2, sta.latitude, sta.longitude, sta.elevation, '2')
                tr1.write(file1, format='sac')
                tr2.write(file2, format='sac')

            # Extract traces - P
            if "P" in opts.channels:
                trP = stp[0]
                trP = utils.update_stats(trP, sta.latitude, sta.longitude, sta.elevation, 'P')
                trP.write(fileP, format='sac')

            t1 += dt
            t2 += dt


if __name__ == "__main__":

    # Run main program
    main()