# -*- coding: utf-8 -*-

import sys, os, time, pprint, config as cfg
from subprocess import Popen
from datetime import datetime, timedelta
from remotecaller import xmlrpc

script_path = os.path.dirname(sys.argv[0])
torrent_magnet = int(sys.argv[1])
torrent_name = sys.argv[2]
torrent_label = sys.argv[3]
torrent_hash = sys.argv[4]
torrent_path = sys.argv[5]
torrent_size = int(sys.argv[6]) / 1073741824.0

def imdb_search():

        try:
                from threading import Thread
                from guessit import guessit
                from imdbpie import Imdb

                def imdb_ratings():
                        ratings.update(imdb.get_title_ratings(movie_imdb))

                def movie_country():
                        country.extend(imdb.get_title_versions(movie_imdb)['origins'])

                imdb = Imdb()
                torrent_info = guessit(torrent_name)
                movie_title = torrent_info['title'] + ' ' + str(torrent_info['year'])
                movie_imdb = imdb.search_for_title(movie_title)[0]['imdb_id']

                ratings = {}
                country = []
                t1 = Thread(target=movie_country)
                t2 = Thread(target=imdb_ratings)
                t1.start()
                t2.start()
                t1.join()
                t2.join()
        except:
                return

        rating = ratings['rating']
        votes = ratings['ratingCount']

        if rating < minimum_rating or votes < minimum_votes:
                xmlrpc('d.erase', (torrent_hash,))
                sys.exit()

        if skip_foreign and 'US' not in country:
                xmlrpc('d.erase', (torrent_hash,))
                sys.exit()

if torrent_magnet:
        xmlrpc('d.start', (torrent_hash,))
        sys.exit()

if torrent_label in cfg.imdb:
        minimum_rating, minimum_votes, skip_foreign = cfg.imdb[torrent_label]
        imdb_search()

if cfg.enable_disk_check:
        queue = script_path + '/queue.txt'

        with open(queue, 'a+') as txt:
                txt.write(torrent_hash + '\n')

        time.sleep(0.001)

        while True:

                try:
                        with open(queue, 'r') as txt:
                                queued = txt.read().strip().splitlines()
                except:
                        with open(queue, 'a+') as txt:
                                txt.write(torrent_hash + '\n')

                try:
                        if queued[0] == torrent_hash:
                                break

                        if torrent_hash not in queued:

                                with open(queue, 'a') as txt:
                                        txt.write(torrent_hash + '\n')
                except:
                        pass

                time.sleep(0.01)

        try:
                from torrents import completed
                from mountpoints import mount_points
        except:
                import cacher
                cacher.build_cache('checker')
                from torrents import completed
                from mountpoints import mount_points

        current_time = datetime.now()
        remover = script_path + '/remover.py'
        remover_queue = script_path + '/' + torrent_hash + '.txt'
        subtractions = script_path + '/' + torrent_hash + 'sub.txt'
        emailer = script_path + '/emailer.py'
        mount_point = [path for path in [torrent_path.rsplit('/', num)[0] for num in range(torrent_path.count('/'))] if os.path.ismount(path)]
        mount_point = mount_point[0] if mount_point else '/'

        try:
                from torrent_history import torrents, recent_torrents

                downloading = xmlrpc('d.multicall2', ('', 'leeching', 'd.left_bytes=', 'd.hash='))
                downloading = sum(t_bytes for t_bytes, t_hash in downloading if t_hash != torrent_hash and torrents[t_hash] == mount_point)
                torrents[torrent_hash] = mount_point
                additions = []
                recent_torrents = [x for x in recent_torrents if current_time - x[1] < timedelta(minutes=3)]
                d_queue = [(t_hash, additions.append(t_bytes)) for m_point, d_time, t_hash, t_bytes in recent_torrents if m_point == mount_point]
                d_queue = [x[0] for x in d_queue]

                try:
                        unaccounted = sum(additions) - sum(int(open(script_path + '/' + t_hash + 'sub.txt').read()) for t_hash in d_queue)
                except:
                        unaccounted = 0
        except:
                torrents = {}
                downloading = xmlrpc('d.multicall2', ('', 'leeching', 'd.directory=', 'd.hash=', 'd.left_bytes='))

                for t_directory, t_hash, t_bytes in downloading:
                        mp = [path for path in [t_directory.rsplit('/', num)[0] for num in range(t_directory.count('/'))] if os.path.ismount(path)]
                        mp = mp[0] if mp else '/'
                        torrents[t_hash] = mp

                downloading = sum(t_bytes for t_directory, t_hash, t_bytes in downloading if t_hash != torrent_hash and torrents[t_hash] == mount_point)
                recent_torrents = []
                unaccounted = 0

        disk = os.statvfs(mount_point)
        available_space = (disk.f_bsize * disk.f_bavail + unaccounted - downloading) / 1073741824.0
        minimum_space = cfg.minimum_space_mp[mount_point] if mount_point in cfg.minimum_space_mp else cfg.minimum_space
        required_space = torrent_size - (available_space - minimum_space)
        requirements = cfg.minimum_size, cfg.minimum_age, cfg.minimum_ratio, cfg.fallback_age, cfg.fallback_ratio
        include = override = True
        exclude = mp_updated = no = False
        freed_space = deleted = 0
        fallback_torrents = []

        while freed_space < required_space:

                if not completed and not fallback_torrents:
                        break

                if completed:
                        t_age, t_label, t_tracker, t_ratio, t_size_b, t_name, t_hash, t_path, parent_directory = completed[0]

                        if override:
                                override = False
                                min_size, min_age, min_ratio, fb_age, fb_ratio = requirements

                        if cfg.exclude_unlabelled and not t_label:
                                del completed[0]
                                continue

                        if cfg.labels:

                                if t_label in cfg.labels:
                                        label_rule = cfg.labels[t_label]
                                        rule = label_rule[0]

                                        if rule is exclude:
                                                del completed[0]
                                                continue

                                        if rule is not include:
                                                override = True
                                                min_size, min_age, min_ratio, fb_age, fb_ratio = label_rule

                                elif cfg.labels_only:
                                        del completed[0]
                                        continue

                        if cfg.trackers and not override:
                                tracker_rule = [tracker for tracker in cfg.trackers for url in t_tracker if tracker in url[0]]

                                if tracker_rule:
                                        tracker_rule = cfg.trackers[tracker_rule[0]]
                                        rule = tracker_rule[0]

                                        if rule is exclude:
                                                del completed[0]
                                                continue

                                        if rule is not include:
                                                override = True
                                                min_size, min_age, min_ratio, fb_age, fb_ratio = tracker_rule

                                elif cfg.trackers_only:
                                        del completed[0]
                                        continue

                        t_age = (current_time - datetime.utcfromtimestamp(t_age)).days
                        t_ratio /= 1000.0
                        t_size_g = t_size_b / 1073741824.0

                        if t_age < min_age or t_ratio < min_ratio or t_size_g < min_size:

                                if fb_age is not no and t_age >= fb_age and t_size_g >= min_size:
                                        fallback_torrents.append((parent_directory, t_hash, t_path, t_size_b, t_size_g))

                                elif fb_ratio is not no and t_ratio >= fb_ratio and t_size_g >= min_size:
                                        fallback_torrents.append((parent_directory, t_hash, t_path, t_size_b, t_size_g))

                                del completed[0]
                                continue

                        del completed[0]
                else:
                        parent_directory, t_hash, t_path, t_size_b, t_size_g = fallback_torrents[0]
                        del fallback_torrents[0]

                if parent_directory not in mount_points:
                        mp_updated = True
                        t_mp = [path for path in [parent_directory.rsplit('/', num)[0] for num in range(parent_directory.count('/'))] if os.path.ismount(path)]
                        t_mp = t_mp[0] if t_mp else '/'
                        mount_points[parent_directory] = t_mp

                if mount_points[parent_directory] != mount_point:
                        continue

                try:
                        xmlrpc('d.open', (t_hash,))
                except:
                        continue

                if not deleted:
                        open(subtractions, mode='w+').write('0')

                Popen([sys.executable, remover, remover_queue, t_hash, t_path, subtractions])
                deleted += t_size_b
                freed_space += t_size_g

        if freed_space >= required_space:
                xmlrpc('d.start', (torrent_hash,))

        if mp_updated:
                open(script_path + '/mountpoints.py', mode='w+').write('mount_points = ' + pprint.pformat(mount_points))

        recent_torrents.insert(0, (mount_point, current_time, torrent_hash, deleted))
        open(script_path + '/torrent_history.py', mode='w+').write('import datetime\n\ntorrents = ' + pprint.pformat(torrents)
                                                                 + '\n\nrecent_torrents = ' + pprint.pformat(recent_torrents))

        queue = open(queue, mode='r+')
        queued = queue.read().strip().splitlines()
        queue.seek(0)
        [queue.write(torrent + '\n') for torrent in queued if torrent != torrent_hash]
        queue.truncate()

        if freed_space < required_space and cfg.enable_email:
                Popen([sys.executable, emailer])

        time.sleep(300)
        os.remove(subtractions)
else:
        xmlrpc('d.start', (torrent_hash,))
