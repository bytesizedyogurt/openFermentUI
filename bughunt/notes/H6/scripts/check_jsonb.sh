#!/usr/bin/env bash
# check_jsonb.sh: the data type of every content column (body, record, selection, settings, input, result) of
# schema openferment on a database the head's migrations make from empty (bh_h6_jsonb, dropped after).
source /home/user/openFermentUI/bughunt/lib/env.sh
bh_db_fresh bh_h6_jsonb || exit 1
psql "$BH_SERVER/bh_h6_jsonb" -XAtc "select data_type, count(*), string_agg(distinct column_name, ',') from information_schema.columns where table_schema='openferment' and column_name in ('body','record','selection','settings','input','result') group by 1"
bh_db_drop bh_h6_jsonb
