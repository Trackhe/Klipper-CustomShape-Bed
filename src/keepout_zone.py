# Keepout zones for Klipper — block moves into configured XY regions
#
# Copyright (C) 2026
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging

# Geometry helpers (pure functions — also used by tests)


def point_in_rect(x, y, xmin, ymin, xmax, ymax):
    return xmin <= x <= xmax and ymin <= y <= ymax


def segment_intersects_rect(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
    """True if the open/closed segment from (x0,y0) to (x1,y1) hits the AABB.

    Uses Liang-Barsky clipping. Also returns True if either endpoint is inside.
    """
    if point_in_rect(x0, y0, xmin, ymin, xmax, ymax):
        return True
    if point_in_rect(x1, y1, xmin, ymin, xmax, ymax):
        return True

    dx = x1 - x0
    dy = y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in (
        (-dx, x0 - xmin),  # left
        (dx, xmax - x0),   # right
        (-dy, y0 - ymin),  # bottom
        (dy, ymax - y0),   # top
    ):
        if p == 0.0:
            if q < 0.0:
                return False
            continue
        r = q / p
        if p < 0.0:
            if r > t1:
                return False
            if r > t0:
                t0 = r
        else:
            if r < t0:
                return False
            if r < t1:
                t1 = r
    return t0 <= t1


def expand_rect(xmin, ymin, xmax, ymax, margin):
    return (xmin - margin, ymin - margin, xmax + margin, ymax + margin)


class KeepoutZone:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.next_transform = None
        self.enabled = config.getboolean('enabled', True)
        self.margin = config.getfloat('margin', 0.0, minval=0.0)
        # If set, keepouts only apply when nozzle Z is at or below this height
        self.z_max = config.getfloat('z_max', None, above=0.0)
        self.zones = self._parse_zones(config)

        if not self.zones:
            raise config.error(
                "keepout_zone: define at least one zone "
                "(zone_1_min / zone_1_max, ...)"
            )

        self.printer.register_event_handler('klippy:connect', self._handle_connect)
        self.printer.register_event_handler('klippy:ready', self._handle_ready)

        self.gcode.register_command(
            'KEEPOUT_ZONE', self.cmd_KEEPOUT_ZONE,
            desc=self.cmd_KEEPOUT_ZONE_help)
        self.gcode.register_command(
            'KEEPOUT_ZONE_STATUS', self.cmd_KEEPOUT_ZONE_STATUS,
            desc=self.cmd_KEEPOUT_ZONE_STATUS_help)

        logging.info(
            "keepout_zone: %d zone(s), margin=%.3f, enabled=%s, z_max=%s",
            len(self.zones), self.margin, self.enabled, self.z_max
        )

    def _parse_zones(self, config):
        zones = []
        for i in range(1, 100):
            min_opt = 'zone_%d_min' % (i,)
            max_opt = 'zone_%d_max' % (i,)
            if config.get(min_opt, None) is None:
                if config.get(max_opt, None) is not None:
                    raise config.error(
                        "keepout_zone: %s without %s" % (max_opt, min_opt)
                    )
                break
            if config.get(max_opt, None) is None:
                raise config.error(
                    "keepout_zone: %s without %s" % (min_opt, max_opt)
                )
            xmin, ymin = config.getfloatlist(min_opt, count=2)
            xmax, ymax = config.getfloatlist(max_opt, count=2)
            if xmax < xmin or ymax < ymin:
                raise config.error(
                    "keepout_zone: zone_%d max must be >= min" % (i,)
                )
            name = config.get('zone_%d_name' % (i,), 'zone_%d' % (i,))
            zones.append({
                'name': name,
                'min': (xmin, ymin),
                'max': (xmax, ymax),
            })
        return zones

    def _handle_connect(self):
        self.toolhead = self.printer.lookup_object('toolhead')

    def _handle_ready(self):
        if self.next_transform is None:
            self.next_transform = self.gcode_move.set_move_transform(
                self, force=True
            )

    def _effective_rects(self):
        rects = []
        for z in self.zones:
            xmin, ymin = z['min']
            xmax, ymax = z['max']
            if self.margin:
                xmin, ymin, xmax, ymax = expand_rect(
                    xmin, ymin, xmax, ymax, self.margin
                )
            rects.append((z['name'], xmin, ymin, xmax, ymax))
        return rects

    def _z_applies(self, z):
        if self.z_max is None:
            return True
        return z <= self.z_max + 1e-9

    def _find_violation(self, x0, y0, x1, y1, z):
        if not self.enabled:
            return None
        if not self._z_applies(z):
            return None
        for name, xmin, ymin, xmax, ymax in self._effective_rects():
            if segment_intersects_rect(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
                return name
        return None

    def get_position(self):
        return self.next_transform.get_position()

    def move(self, newpos, speed):
        cur = self.next_transform.get_position()
        # newpos / cur are gcode coordinates (same frame as printer.cfg XY)
        viol = self._find_violation(
            cur[0], cur[1], newpos[0], newpos[1], newpos[2]
        )
        if viol is not None:
            raise self.gcode.error(
                "keepout_zone: move blocked — path enters '%s' "
                "(from %.3f,%.3f to %.3f,%.3f, Z=%.3f). "
                "Use KEEPOUT_ZONE ENABLE=0 only for recovery."
                % (viol, cur[0], cur[1], newpos[0], newpos[1], newpos[2])
            )
        self.next_transform.move(newpos, speed)

    def get_status(self, eventtime=None):
        return {
            'enabled': self.enabled,
            'margin': self.margin,
            'z_max': self.z_max,
            'zones': [
                {
                    'name': z['name'],
                    'min': list(z['min']),
                    'max': list(z['max']),
                }
                for z in self.zones
            ],
        }

    cmd_KEEPOUT_ZONE_help = "Enable/disable keepout zone enforcement"
    def cmd_KEEPOUT_ZONE(self, gcmd):
        enable = gcmd.get_int('ENABLE', None)
        if enable is None:
            gcmd.respond_info(
                "keepout_zone: enabled=%s (set ENABLE=0/1)" % (self.enabled,)
            )
            return
        self.enabled = bool(enable)
        gcmd.respond_info("keepout_zone: enabled=%s" % (self.enabled,))

    cmd_KEEPOUT_ZONE_STATUS_help = "Report configured keepout zones"
    def cmd_KEEPOUT_ZONE_STATUS(self, gcmd):
        gcmd.respond_info(
            "keepout_zone: enabled=%s margin=%.3f z_max=%s"
            % (self.enabled, self.margin, self.z_max)
        )
        for name, xmin, ymin, xmax, ymax in self._effective_rects():
            gcmd.respond_info(
                "  %s (with margin): [%.3f,%.3f] .. [%.3f,%.3f]"
                % (name, xmin, ymin, xmax, ymax)
            )


def load_config(config):
    return KeepoutZone(config)
