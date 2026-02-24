import React from 'react';
import { StyleSheet, View, Text, Image } from 'react-native';
import { COLORS } from '../constants';
import { formatDate } from '../utils/schedule';

export function MovieCard({ movie }) {
  return (
    <View style={styles.card}>
      {movie.poster_url ? (
        <Image source={{ uri: movie.poster_url }} style={styles.poster} resizeMode="cover" />
      ) : (
        <View style={styles.posterPlaceholder} />
      )}
      <View style={styles.body}>
        <Text style={styles.movieTitle}>{movie.title}</Text>
        {Object.entries(movie.theaters).map(([theaterName, schedule]) => (
          <View key={theaterName} style={styles.theaterBlock}>
            <Text style={styles.theaterName}>{theaterName}</Text>
            {schedule.map(s => (
              <View key={s.date} style={styles.scheduleRow}>
                <Text style={styles.scheduleDate}>{formatDate(s.date)}</Text>
                <Text style={styles.scheduleTimes}>{s.times.join('  ')}</Text>
              </View>
            ))}
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.white,
    borderRadius: 12,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    overflow: 'hidden',
  },
  poster: {
    width: '100%',
    height: 140,
  },
  posterPlaceholder: {
    width: '100%',
    height: 4,
    backgroundColor: COLORS.primary,
  },
  body: { padding: 14 },
  movieTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.primary,
    marginBottom: 10,
    lineHeight: 22,
  },
  theaterBlock: { marginBottom: 10 },
  theaterName: {
    fontSize: 12,
    fontWeight: '600',
    color: COLORS.textLight,
    backgroundColor: COLORS.cardBg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    alignSelf: 'flex-start',
    marginBottom: 5,
  },
  scheduleRow: {
    flexDirection: 'row',
    paddingVertical: 2,
    paddingHorizontal: 4,
  },
  scheduleDate: {
    fontSize: 13,
    color: COLORS.textLight,
    width: 82,
  },
  scheduleTimes: {
    fontSize: 14,
    color: COLORS.primary,
    fontWeight: '500',
    flex: 1,
  },
});
