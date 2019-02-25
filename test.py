from remotecall import xmlrpc

try:
        xmlrpc('d.multicall2', ('', 'leeching', 'd.down.total='))
except:
        print('SCGI address not configured properly. Please adjust it in your config.py file before continuing.')
        quit()

print("\nTA = Torrent Age  TN = Torrent Name  TL = Torrent Label  TT = Torrent Tracker\n")

import sys, os, config as cfg
from datetime import datetime

try:
    from urllib import parse as urllib
except:
    import urllib

startTime = datetime.now()

torrent_size = float(sys.argv[1])

if cfg.enable_disk_check:
        completed = xmlrpc('d.multicall2', ('', 'complete', 'd.timestamp.finished=', 'd.custom1=', 't.multicall=,t.url=', 'd.ratio=', 'd.size_bytes=', 'd.base_path=', 'd.name='))
        completed.sort()
        disk = os.statvfs('/')
        available_space = disk.f_bsize * disk.f_bavail / 1073741824.0
        fallback_torrents = []
        min_size = cfg.minimum_size
        min_age = cfg.minimum_age
        min_ratio = cfg.minimum_ratio
        fb_age = cfg.fallback_age
        fb_ratio = cfg.fallback_ratio
        include = True
        exclude = False
        fallback = False
        override = False
        no = False
        deleted = []
        count = 0
        zero = 0
        required_space = torrent_size - (available_space - cfg.minimum_space)

        while zero < required_space:

                if not completed and not fallback and fallback_torrents:
                        fallback = True

                if not fallback:
                        t_age, t_label, t_tracker, t_ratio, t_size, t_path, t_name = completed[0]
                        t_label = urllib.unquote(t_label)

                        if override:
                                override = False
                                min_size = cfg.minimum_size
                                min_age = cfg.minimum_age
                                min_ratio = cfg.minimum_ratio
                                fb_age = cfg.fallback_age
                                fb_ratio = cfg.fallback_ratio

                        if cfg.exclude_unlabelled and not t_label:
                                del completed[0]

                                if not completed and not fallback_torrents:
                                        break

                                continue

                        if cfg.labels:

                                if t_label in cfg.labels:

                                        if not cfg.labels[t_label][0]:
                                                del completed[0]

                                                if not completed and not fallback_torrents:
                                                        break

                                                continue

                                        elif cfg.labels[t_label][0] is not include:
                                                override = True
                                                min_size, min_age, min_ratio, fb_age, fb_ratio = cfg.labels[t_label]

                                elif cfg.labels_only:
                                        del completed[0]

                                        if not completed and not fallback_torrents:
                                                break

                                        continue

                        if cfg.trackers and not override:
                                rule = [rule for rule in cfg.trackers for url in t_tracker if rule in url[0]]

                                if rule:
                                        rule = rule[0]

                                        if not cfg.trackers[rule][0]:
                                                del completed[0]

                                                if not completed and not fallback_torrents:
                                                        break

                                                continue

                                        elif cfg.trackers[rule][0] is not include:
                                                override = True
                                                min_size, min_age, min_ratio, fb_age, fb_ratio = cfg.trackers[rule]

                                elif cfg.trackers_only:
                                        del completed[0]

                                        if not completed and not fallback_torrents:
                                                break

                                        continue

                        t_age = (datetime.now() - datetime.utcfromtimestamp(t_age)).days
                        t_ratio /= 1000.0
                        t_size /= 1073741824.0

                        if t_age < min_age or t_ratio < min_ratio or t_size < min_size:

                                if fb_age is not no and t_age >= fb_age and t_size >= min_size:
                                        fallback_torrents.append([t_age, t_label, t_tracker, t_size, t_name])

                                elif fb_ratio is not no and t_ratio >= fb_ratio and t_size >= min_size:
                                        fallback_torrents.append([t_age, t_label, t_tracker, t_size, t_name])

                                del completed[0]

                                if not completed:

                                        if fallback_torrents:
                                                continue

                                        break

                                continue
                else:
                        t_age, t_label, t_tracker, t_size, t_name = fallback_torrents[0]

                if not fallback:
                        del completed[0]
                else:
                        del fallback_torrents[0]

                count += 1
                zero += t_size
                deleted.append("%s. TA: %s Days Old\n%s. TN: %s\n%s. TL: %s\n%s. TT: %s\n" % (count, t_age, count, t_name, count, t_label, count, t_tracker))

                if not completed and not fallback_torrents:
                        break

time = datetime.now() - startTime
calc = available_space + zero - torrent_size

with open('testresult.txt', 'w+') as textfile:
        textfile.write("Script Executed in %s Seconds\n%s Torrent(s) Deleted Totaling %.2f GB\n" % (time, count, zero))
        textfile.write("%.2f GB Free Space Before Torrent Download\n%.2f GB Free Space After %.2f GB Torrent Download\n\n" % (available_space, calc, torrent_size))
        textfile.write("TA = Torrent Age  TN = Torrent Name  TL = Torrent Label  TT = Torrent Tracker\n\n")

        for result in deleted:
                textfile.write(result + "\n")

for result in deleted:
        print(result)

print("Script Executed in %s Seconds\n%s Torrent(s) Deleted Totaling %.2f GB" % (time, count, zero))
print("%.2f GB Free Space Before Torrent Download\n%.2f GB Free Space After %.2f GB Torrent Download" % (available_space, calc, torrent_size))
