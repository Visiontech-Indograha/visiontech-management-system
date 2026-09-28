// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_database.dart';

// ignore_for_file: type=lint
class $PendingSyncOperationsTable extends PendingSyncOperations
    with TableInfo<$PendingSyncOperationsTable, PendingSyncRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PendingSyncOperationsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _entityTypeMeta = const VerificationMeta(
    'entityType',
  );
  @override
  late final GeneratedColumn<String> entityType = GeneratedColumn<String>(
    'entity_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _payloadJsonMeta = const VerificationMeta(
    'payloadJson',
  );
  @override
  late final GeneratedColumn<String> payloadJson = GeneratedColumn<String>(
    'payload_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  static const VerificationMeta _attemptCountMeta = const VerificationMeta(
    'attemptCount',
  );
  @override
  late final GeneratedColumn<int> attemptCount = GeneratedColumn<int>(
    'attempt_count',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _lastErrorMeta = const VerificationMeta(
    'lastError',
  );
  @override
  late final GeneratedColumn<String> lastError = GeneratedColumn<String>(
    'last_error',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _deadLetterMeta = const VerificationMeta(
    'deadLetter',
  );
  @override
  late final GeneratedColumn<bool> deadLetter = GeneratedColumn<bool>(
    'dead_letter',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("dead_letter" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    entityType,
    payloadJson,
    createdAt,
    attemptCount,
    lastError,
    deadLetter,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'pending_sync_operations';
  @override
  VerificationContext validateIntegrity(
    Insertable<PendingSyncRow> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('entity_type')) {
      context.handle(
        _entityTypeMeta,
        entityType.isAcceptableOrUnknown(data['entity_type']!, _entityTypeMeta),
      );
    } else if (isInserting) {
      context.missing(_entityTypeMeta);
    }
    if (data.containsKey('payload_json')) {
      context.handle(
        _payloadJsonMeta,
        payloadJson.isAcceptableOrUnknown(
          data['payload_json']!,
          _payloadJsonMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_payloadJsonMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    }
    if (data.containsKey('attempt_count')) {
      context.handle(
        _attemptCountMeta,
        attemptCount.isAcceptableOrUnknown(
          data['attempt_count']!,
          _attemptCountMeta,
        ),
      );
    }
    if (data.containsKey('last_error')) {
      context.handle(
        _lastErrorMeta,
        lastError.isAcceptableOrUnknown(data['last_error']!, _lastErrorMeta),
      );
    }
    if (data.containsKey('dead_letter')) {
      context.handle(
        _deadLetterMeta,
        deadLetter.isAcceptableOrUnknown(data['dead_letter']!, _deadLetterMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  PendingSyncRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PendingSyncRow(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      entityType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}entity_type'],
      )!,
      payloadJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}payload_json'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      attemptCount: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}attempt_count'],
      )!,
      lastError: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}last_error'],
      ),
      deadLetter: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}dead_letter'],
      )!,
    );
  }

  @override
  $PendingSyncOperationsTable createAlias(String alias) {
    return $PendingSyncOperationsTable(attachedDatabase, alias);
  }
}

class PendingSyncRow extends DataClass implements Insertable<PendingSyncRow> {
  final int id;

  /// 'absence' | 'leave' | 'progress_report' | 'vehicle_booking' | 'tool_borrow'
  final String entityType;
  final String payloadJson;
  final DateTime createdAt;

  /// Berapa kali pengiriman baris ini sudah dicoba, dan pesan gagal terakhir.
  /// Kedua kolom ini sudah ada di skema sejak awal tapi TIDAK PERNAH ditulis --
  /// akibatnya tidak ada cara membedakan "baru gagal sekali karena sinyal" dari
  /// "gagal terus karena datanya memang ditolak".
  final int attemptCount;
  final String? lastError;

  /// Berhenti dicoba otomatis: entah ditolak server secara permanen (4xx) atau
  /// sudah melewati batas percobaan. Barisnya SENGAJA tidak dihapus supaya
  /// datanya tidak hilang & user bisa melihat alasannya lalu memutuskan sendiri
  /// (coba lagi / hapus) di layar Antrian Sinkronisasi.
  final bool deadLetter;
  const PendingSyncRow({
    required this.id,
    required this.entityType,
    required this.payloadJson,
    required this.createdAt,
    required this.attemptCount,
    this.lastError,
    required this.deadLetter,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['entity_type'] = Variable<String>(entityType);
    map['payload_json'] = Variable<String>(payloadJson);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['attempt_count'] = Variable<int>(attemptCount);
    if (!nullToAbsent || lastError != null) {
      map['last_error'] = Variable<String>(lastError);
    }
    map['dead_letter'] = Variable<bool>(deadLetter);
    return map;
  }

  PendingSyncOperationsCompanion toCompanion(bool nullToAbsent) {
    return PendingSyncOperationsCompanion(
      id: Value(id),
      entityType: Value(entityType),
      payloadJson: Value(payloadJson),
      createdAt: Value(createdAt),
      attemptCount: Value(attemptCount),
      lastError: lastError == null && nullToAbsent
          ? const Value.absent()
          : Value(lastError),
      deadLetter: Value(deadLetter),
    );
  }

  factory PendingSyncRow.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PendingSyncRow(
      id: serializer.fromJson<int>(json['id']),
      entityType: serializer.fromJson<String>(json['entityType']),
      payloadJson: serializer.fromJson<String>(json['payloadJson']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      attemptCount: serializer.fromJson<int>(json['attemptCount']),
      lastError: serializer.fromJson<String?>(json['lastError']),
      deadLetter: serializer.fromJson<bool>(json['deadLetter']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'entityType': serializer.toJson<String>(entityType),
      'payloadJson': serializer.toJson<String>(payloadJson),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'attemptCount': serializer.toJson<int>(attemptCount),
      'lastError': serializer.toJson<String?>(lastError),
      'deadLetter': serializer.toJson<bool>(deadLetter),
    };
  }

  PendingSyncRow copyWith({
    int? id,
    String? entityType,
    String? payloadJson,
    DateTime? createdAt,
    int? attemptCount,
    Value<String?> lastError = const Value.absent(),
    bool? deadLetter,
  }) => PendingSyncRow(
    id: id ?? this.id,
    entityType: entityType ?? this.entityType,
    payloadJson: payloadJson ?? this.payloadJson,
    createdAt: createdAt ?? this.createdAt,
    attemptCount: attemptCount ?? this.attemptCount,
    lastError: lastError.present ? lastError.value : this.lastError,
    deadLetter: deadLetter ?? this.deadLetter,
  );
  PendingSyncRow copyWithCompanion(PendingSyncOperationsCompanion data) {
    return PendingSyncRow(
      id: data.id.present ? data.id.value : this.id,
      entityType: data.entityType.present
          ? data.entityType.value
          : this.entityType,
      payloadJson: data.payloadJson.present
          ? data.payloadJson.value
          : this.payloadJson,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      attemptCount: data.attemptCount.present
          ? data.attemptCount.value
          : this.attemptCount,
      lastError: data.lastError.present ? data.lastError.value : this.lastError,
      deadLetter: data.deadLetter.present
          ? data.deadLetter.value
          : this.deadLetter,
    );
  }

  @override
  String toString() {
    return (StringBuffer('PendingSyncRow(')
          ..write('id: $id, ')
          ..write('entityType: $entityType, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('createdAt: $createdAt, ')
          ..write('attemptCount: $attemptCount, ')
          ..write('lastError: $lastError, ')
          ..write('deadLetter: $deadLetter')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    entityType,
    payloadJson,
    createdAt,
    attemptCount,
    lastError,
    deadLetter,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PendingSyncRow &&
          other.id == this.id &&
          other.entityType == this.entityType &&
          other.payloadJson == this.payloadJson &&
          other.createdAt == this.createdAt &&
          other.attemptCount == this.attemptCount &&
          other.lastError == this.lastError &&
          other.deadLetter == this.deadLetter);
}

class PendingSyncOperationsCompanion extends UpdateCompanion<PendingSyncRow> {
  final Value<int> id;
  final Value<String> entityType;
  final Value<String> payloadJson;
  final Value<DateTime> createdAt;
  final Value<int> attemptCount;
  final Value<String?> lastError;
  final Value<bool> deadLetter;
  const PendingSyncOperationsCompanion({
    this.id = const Value.absent(),
    this.entityType = const Value.absent(),
    this.payloadJson = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.attemptCount = const Value.absent(),
    this.lastError = const Value.absent(),
    this.deadLetter = const Value.absent(),
  });
  PendingSyncOperationsCompanion.insert({
    this.id = const Value.absent(),
    required String entityType,
    required String payloadJson,
    this.createdAt = const Value.absent(),
    this.attemptCount = const Value.absent(),
    this.lastError = const Value.absent(),
    this.deadLetter = const Value.absent(),
  }) : entityType = Value(entityType),
       payloadJson = Value(payloadJson);
  static Insertable<PendingSyncRow> custom({
    Expression<int>? id,
    Expression<String>? entityType,
    Expression<String>? payloadJson,
    Expression<DateTime>? createdAt,
    Expression<int>? attemptCount,
    Expression<String>? lastError,
    Expression<bool>? deadLetter,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (entityType != null) 'entity_type': entityType,
      if (payloadJson != null) 'payload_json': payloadJson,
      if (createdAt != null) 'created_at': createdAt,
      if (attemptCount != null) 'attempt_count': attemptCount,
      if (lastError != null) 'last_error': lastError,
      if (deadLetter != null) 'dead_letter': deadLetter,
    });
  }

  PendingSyncOperationsCompanion copyWith({
    Value<int>? id,
    Value<String>? entityType,
    Value<String>? payloadJson,
    Value<DateTime>? createdAt,
    Value<int>? attemptCount,
    Value<String?>? lastError,
    Value<bool>? deadLetter,
  }) {
    return PendingSyncOperationsCompanion(
      id: id ?? this.id,
      entityType: entityType ?? this.entityType,
      payloadJson: payloadJson ?? this.payloadJson,
      createdAt: createdAt ?? this.createdAt,
      attemptCount: attemptCount ?? this.attemptCount,
      lastError: lastError ?? this.lastError,
      deadLetter: deadLetter ?? this.deadLetter,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (entityType.present) {
      map['entity_type'] = Variable<String>(entityType.value);
    }
    if (payloadJson.present) {
      map['payload_json'] = Variable<String>(payloadJson.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (attemptCount.present) {
      map['attempt_count'] = Variable<int>(attemptCount.value);
    }
    if (lastError.present) {
      map['last_error'] = Variable<String>(lastError.value);
    }
    if (deadLetter.present) {
      map['dead_letter'] = Variable<bool>(deadLetter.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PendingSyncOperationsCompanion(')
          ..write('id: $id, ')
          ..write('entityType: $entityType, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('createdAt: $createdAt, ')
          ..write('attemptCount: $attemptCount, ')
          ..write('lastError: $lastError, ')
          ..write('deadLetter: $deadLetter')
          ..write(')'))
        .toString();
  }
}

class $CachedSyncGroupsTable extends CachedSyncGroups
    with TableInfo<$CachedSyncGroupsTable, CachedSyncGroupRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedSyncGroupsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _syncGroupMeta = const VerificationMeta(
    'syncGroup',
  );
  @override
  late final GeneratedColumn<String> syncGroup = GeneratedColumn<String>(
    'sync_group',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _dataJsonMeta = const VerificationMeta(
    'dataJson',
  );
  @override
  late final GeneratedColumn<String> dataJson = GeneratedColumn<String>(
    'data_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _lastSyncedAtMeta = const VerificationMeta(
    'lastSyncedAt',
  );
  @override
  late final GeneratedColumn<DateTime> lastSyncedAt = GeneratedColumn<DateTime>(
    'last_synced_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [syncGroup, dataJson, lastSyncedAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_sync_groups';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedSyncGroupRow> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('sync_group')) {
      context.handle(
        _syncGroupMeta,
        syncGroup.isAcceptableOrUnknown(data['sync_group']!, _syncGroupMeta),
      );
    } else if (isInserting) {
      context.missing(_syncGroupMeta);
    }
    if (data.containsKey('data_json')) {
      context.handle(
        _dataJsonMeta,
        dataJson.isAcceptableOrUnknown(data['data_json']!, _dataJsonMeta),
      );
    } else if (isInserting) {
      context.missing(_dataJsonMeta);
    }
    if (data.containsKey('last_synced_at')) {
      context.handle(
        _lastSyncedAtMeta,
        lastSyncedAt.isAcceptableOrUnknown(
          data['last_synced_at']!,
          _lastSyncedAtMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_lastSyncedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {syncGroup};
  @override
  CachedSyncGroupRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedSyncGroupRow(
      syncGroup: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sync_group'],
      )!,
      dataJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}data_json'],
      )!,
      lastSyncedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}last_synced_at'],
      )!,
    );
  }

  @override
  $CachedSyncGroupsTable createAlias(String alias) {
    return $CachedSyncGroupsTable(attachedDatabase, alias);
  }
}

class CachedSyncGroupRow extends DataClass
    implements Insertable<CachedSyncGroupRow> {
  final String syncGroup;
  final String dataJson;
  final DateTime lastSyncedAt;
  const CachedSyncGroupRow({
    required this.syncGroup,
    required this.dataJson,
    required this.lastSyncedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['sync_group'] = Variable<String>(syncGroup);
    map['data_json'] = Variable<String>(dataJson);
    map['last_synced_at'] = Variable<DateTime>(lastSyncedAt);
    return map;
  }

  CachedSyncGroupsCompanion toCompanion(bool nullToAbsent) {
    return CachedSyncGroupsCompanion(
      syncGroup: Value(syncGroup),
      dataJson: Value(dataJson),
      lastSyncedAt: Value(lastSyncedAt),
    );
  }

  factory CachedSyncGroupRow.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedSyncGroupRow(
      syncGroup: serializer.fromJson<String>(json['syncGroup']),
      dataJson: serializer.fromJson<String>(json['dataJson']),
      lastSyncedAt: serializer.fromJson<DateTime>(json['lastSyncedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'syncGroup': serializer.toJson<String>(syncGroup),
      'dataJson': serializer.toJson<String>(dataJson),
      'lastSyncedAt': serializer.toJson<DateTime>(lastSyncedAt),
    };
  }

  CachedSyncGroupRow copyWith({
    String? syncGroup,
    String? dataJson,
    DateTime? lastSyncedAt,
  }) => CachedSyncGroupRow(
    syncGroup: syncGroup ?? this.syncGroup,
    dataJson: dataJson ?? this.dataJson,
    lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
  );
  CachedSyncGroupRow copyWithCompanion(CachedSyncGroupsCompanion data) {
    return CachedSyncGroupRow(
      syncGroup: data.syncGroup.present ? data.syncGroup.value : this.syncGroup,
      dataJson: data.dataJson.present ? data.dataJson.value : this.dataJson,
      lastSyncedAt: data.lastSyncedAt.present
          ? data.lastSyncedAt.value
          : this.lastSyncedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedSyncGroupRow(')
          ..write('syncGroup: $syncGroup, ')
          ..write('dataJson: $dataJson, ')
          ..write('lastSyncedAt: $lastSyncedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(syncGroup, dataJson, lastSyncedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedSyncGroupRow &&
          other.syncGroup == this.syncGroup &&
          other.dataJson == this.dataJson &&
          other.lastSyncedAt == this.lastSyncedAt);
}

class CachedSyncGroupsCompanion extends UpdateCompanion<CachedSyncGroupRow> {
  final Value<String> syncGroup;
  final Value<String> dataJson;
  final Value<DateTime> lastSyncedAt;
  final Value<int> rowid;
  const CachedSyncGroupsCompanion({
    this.syncGroup = const Value.absent(),
    this.dataJson = const Value.absent(),
    this.lastSyncedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedSyncGroupsCompanion.insert({
    required String syncGroup,
    required String dataJson,
    required DateTime lastSyncedAt,
    this.rowid = const Value.absent(),
  }) : syncGroup = Value(syncGroup),
       dataJson = Value(dataJson),
       lastSyncedAt = Value(lastSyncedAt);
  static Insertable<CachedSyncGroupRow> custom({
    Expression<String>? syncGroup,
    Expression<String>? dataJson,
    Expression<DateTime>? lastSyncedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (syncGroup != null) 'sync_group': syncGroup,
      if (dataJson != null) 'data_json': dataJson,
      if (lastSyncedAt != null) 'last_synced_at': lastSyncedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedSyncGroupsCompanion copyWith({
    Value<String>? syncGroup,
    Value<String>? dataJson,
    Value<DateTime>? lastSyncedAt,
    Value<int>? rowid,
  }) {
    return CachedSyncGroupsCompanion(
      syncGroup: syncGroup ?? this.syncGroup,
      dataJson: dataJson ?? this.dataJson,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (syncGroup.present) {
      map['sync_group'] = Variable<String>(syncGroup.value);
    }
    if (dataJson.present) {
      map['data_json'] = Variable<String>(dataJson.value);
    }
    if (lastSyncedAt.present) {
      map['last_synced_at'] = Variable<DateTime>(lastSyncedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedSyncGroupsCompanion(')
          ..write('syncGroup: $syncGroup, ')
          ..write('dataJson: $dataJson, ')
          ..write('lastSyncedAt: $lastSyncedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $PendingAttachmentsTable extends PendingAttachments
    with TableInfo<$PendingAttachmentsTable, PendingAttachmentRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PendingAttachmentsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _endpointMeta = const VerificationMeta(
    'endpoint',
  );
  @override
  late final GeneratedColumn<String> endpoint = GeneratedColumn<String>(
    'endpoint',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _localFilePathMeta = const VerificationMeta(
    'localFilePath',
  );
  @override
  late final GeneratedColumn<String> localFilePath = GeneratedColumn<String>(
    'local_file_path',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _labelMeta = const VerificationMeta('label');
  @override
  late final GeneratedColumn<String> label = GeneratedColumn<String>(
    'label',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  static const VerificationMeta _attemptCountMeta = const VerificationMeta(
    'attemptCount',
  );
  @override
  late final GeneratedColumn<int> attemptCount = GeneratedColumn<int>(
    'attempt_count',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _lastErrorMeta = const VerificationMeta(
    'lastError',
  );
  @override
  late final GeneratedColumn<String> lastError = GeneratedColumn<String>(
    'last_error',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _deadLetterMeta = const VerificationMeta(
    'deadLetter',
  );
  @override
  late final GeneratedColumn<bool> deadLetter = GeneratedColumn<bool>(
    'dead_letter',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("dead_letter" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    endpoint,
    localFilePath,
    label,
    createdAt,
    attemptCount,
    lastError,
    deadLetter,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'pending_attachments';
  @override
  VerificationContext validateIntegrity(
    Insertable<PendingAttachmentRow> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('endpoint')) {
      context.handle(
        _endpointMeta,
        endpoint.isAcceptableOrUnknown(data['endpoint']!, _endpointMeta),
      );
    } else if (isInserting) {
      context.missing(_endpointMeta);
    }
    if (data.containsKey('local_file_path')) {
      context.handle(
        _localFilePathMeta,
        localFilePath.isAcceptableOrUnknown(
          data['local_file_path']!,
          _localFilePathMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_localFilePathMeta);
    }
    if (data.containsKey('label')) {
      context.handle(
        _labelMeta,
        label.isAcceptableOrUnknown(data['label']!, _labelMeta),
      );
    } else if (isInserting) {
      context.missing(_labelMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    }
    if (data.containsKey('attempt_count')) {
      context.handle(
        _attemptCountMeta,
        attemptCount.isAcceptableOrUnknown(
          data['attempt_count']!,
          _attemptCountMeta,
        ),
      );
    }
    if (data.containsKey('last_error')) {
      context.handle(
        _lastErrorMeta,
        lastError.isAcceptableOrUnknown(data['last_error']!, _lastErrorMeta),
      );
    }
    if (data.containsKey('dead_letter')) {
      context.handle(
        _deadLetterMeta,
        deadLetter.isAcceptableOrUnknown(data['dead_letter']!, _deadLetterMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  PendingAttachmentRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PendingAttachmentRow(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      endpoint: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}endpoint'],
      )!,
      localFilePath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}local_file_path'],
      )!,
      label: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}label'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      attemptCount: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}attempt_count'],
      )!,
      lastError: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}last_error'],
      ),
      deadLetter: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}dead_letter'],
      )!,
    );
  }

  @override
  $PendingAttachmentsTable createAlias(String alias) {
    return $PendingAttachmentsTable(attachedDatabase, alias);
  }
}

class PendingAttachmentRow extends DataClass
    implements Insertable<PendingAttachmentRow> {
  final int id;
  final String endpoint;
  final String localFilePath;
  final String label;
  final DateTime createdAt;
  final int attemptCount;
  final String? lastError;
  final bool deadLetter;
  const PendingAttachmentRow({
    required this.id,
    required this.endpoint,
    required this.localFilePath,
    required this.label,
    required this.createdAt,
    required this.attemptCount,
    this.lastError,
    required this.deadLetter,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['endpoint'] = Variable<String>(endpoint);
    map['local_file_path'] = Variable<String>(localFilePath);
    map['label'] = Variable<String>(label);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['attempt_count'] = Variable<int>(attemptCount);
    if (!nullToAbsent || lastError != null) {
      map['last_error'] = Variable<String>(lastError);
    }
    map['dead_letter'] = Variable<bool>(deadLetter);
    return map;
  }

  PendingAttachmentsCompanion toCompanion(bool nullToAbsent) {
    return PendingAttachmentsCompanion(
      id: Value(id),
      endpoint: Value(endpoint),
      localFilePath: Value(localFilePath),
      label: Value(label),
      createdAt: Value(createdAt),
      attemptCount: Value(attemptCount),
      lastError: lastError == null && nullToAbsent
          ? const Value.absent()
          : Value(lastError),
      deadLetter: Value(deadLetter),
    );
  }

  factory PendingAttachmentRow.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PendingAttachmentRow(
      id: serializer.fromJson<int>(json['id']),
      endpoint: serializer.fromJson<String>(json['endpoint']),
      localFilePath: serializer.fromJson<String>(json['localFilePath']),
      label: serializer.fromJson<String>(json['label']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      attemptCount: serializer.fromJson<int>(json['attemptCount']),
      lastError: serializer.fromJson<String?>(json['lastError']),
      deadLetter: serializer.fromJson<bool>(json['deadLetter']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'endpoint': serializer.toJson<String>(endpoint),
      'localFilePath': serializer.toJson<String>(localFilePath),
      'label': serializer.toJson<String>(label),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'attemptCount': serializer.toJson<int>(attemptCount),
      'lastError': serializer.toJson<String?>(lastError),
      'deadLetter': serializer.toJson<bool>(deadLetter),
    };
  }

  PendingAttachmentRow copyWith({
    int? id,
    String? endpoint,
    String? localFilePath,
    String? label,
    DateTime? createdAt,
    int? attemptCount,
    Value<String?> lastError = const Value.absent(),
    bool? deadLetter,
  }) => PendingAttachmentRow(
    id: id ?? this.id,
    endpoint: endpoint ?? this.endpoint,
    localFilePath: localFilePath ?? this.localFilePath,
    label: label ?? this.label,
    createdAt: createdAt ?? this.createdAt,
    attemptCount: attemptCount ?? this.attemptCount,
    lastError: lastError.present ? lastError.value : this.lastError,
    deadLetter: deadLetter ?? this.deadLetter,
  );
  PendingAttachmentRow copyWithCompanion(PendingAttachmentsCompanion data) {
    return PendingAttachmentRow(
      id: data.id.present ? data.id.value : this.id,
      endpoint: data.endpoint.present ? data.endpoint.value : this.endpoint,
      localFilePath: data.localFilePath.present
          ? data.localFilePath.value
          : this.localFilePath,
      label: data.label.present ? data.label.value : this.label,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      attemptCount: data.attemptCount.present
          ? data.attemptCount.value
          : this.attemptCount,
      lastError: data.lastError.present ? data.lastError.value : this.lastError,
      deadLetter: data.deadLetter.present
          ? data.deadLetter.value
          : this.deadLetter,
    );
  }

  @override
  String toString() {
    return (StringBuffer('PendingAttachmentRow(')
          ..write('id: $id, ')
          ..write('endpoint: $endpoint, ')
          ..write('localFilePath: $localFilePath, ')
          ..write('label: $label, ')
          ..write('createdAt: $createdAt, ')
          ..write('attemptCount: $attemptCount, ')
          ..write('lastError: $lastError, ')
          ..write('deadLetter: $deadLetter')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    endpoint,
    localFilePath,
    label,
    createdAt,
    attemptCount,
    lastError,
    deadLetter,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PendingAttachmentRow &&
          other.id == this.id &&
          other.endpoint == this.endpoint &&
          other.localFilePath == this.localFilePath &&
          other.label == this.label &&
          other.createdAt == this.createdAt &&
          other.attemptCount == this.attemptCount &&
          other.lastError == this.lastError &&
          other.deadLetter == this.deadLetter);
}

class PendingAttachmentsCompanion
    extends UpdateCompanion<PendingAttachmentRow> {
  final Value<int> id;
  final Value<String> endpoint;
  final Value<String> localFilePath;
  final Value<String> label;
  final Value<DateTime> createdAt;
  final Value<int> attemptCount;
  final Value<String?> lastError;
  final Value<bool> deadLetter;
  const PendingAttachmentsCompanion({
    this.id = const Value.absent(),
    this.endpoint = const Value.absent(),
    this.localFilePath = const Value.absent(),
    this.label = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.attemptCount = const Value.absent(),
    this.lastError = const Value.absent(),
    this.deadLetter = const Value.absent(),
  });
  PendingAttachmentsCompanion.insert({
    this.id = const Value.absent(),
    required String endpoint,
    required String localFilePath,
    required String label,
    this.createdAt = const Value.absent(),
    this.attemptCount = const Value.absent(),
    this.lastError = const Value.absent(),
    this.deadLetter = const Value.absent(),
  }) : endpoint = Value(endpoint),
       localFilePath = Value(localFilePath),
       label = Value(label);
  static Insertable<PendingAttachmentRow> custom({
    Expression<int>? id,
    Expression<String>? endpoint,
    Expression<String>? localFilePath,
    Expression<String>? label,
    Expression<DateTime>? createdAt,
    Expression<int>? attemptCount,
    Expression<String>? lastError,
    Expression<bool>? deadLetter,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (endpoint != null) 'endpoint': endpoint,
      if (localFilePath != null) 'local_file_path': localFilePath,
      if (label != null) 'label': label,
      if (createdAt != null) 'created_at': createdAt,
      if (attemptCount != null) 'attempt_count': attemptCount,
      if (lastError != null) 'last_error': lastError,
      if (deadLetter != null) 'dead_letter': deadLetter,
    });
  }

  PendingAttachmentsCompanion copyWith({
    Value<int>? id,
    Value<String>? endpoint,
    Value<String>? localFilePath,
    Value<String>? label,
    Value<DateTime>? createdAt,
    Value<int>? attemptCount,
    Value<String?>? lastError,
    Value<bool>? deadLetter,
  }) {
    return PendingAttachmentsCompanion(
      id: id ?? this.id,
      endpoint: endpoint ?? this.endpoint,
      localFilePath: localFilePath ?? this.localFilePath,
      label: label ?? this.label,
      createdAt: createdAt ?? this.createdAt,
      attemptCount: attemptCount ?? this.attemptCount,
      lastError: lastError ?? this.lastError,
      deadLetter: deadLetter ?? this.deadLetter,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (endpoint.present) {
      map['endpoint'] = Variable<String>(endpoint.value);
    }
    if (localFilePath.present) {
      map['local_file_path'] = Variable<String>(localFilePath.value);
    }
    if (label.present) {
      map['label'] = Variable<String>(label.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (attemptCount.present) {
      map['attempt_count'] = Variable<int>(attemptCount.value);
    }
    if (lastError.present) {
      map['last_error'] = Variable<String>(lastError.value);
    }
    if (deadLetter.present) {
      map['dead_letter'] = Variable<bool>(deadLetter.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PendingAttachmentsCompanion(')
          ..write('id: $id, ')
          ..write('endpoint: $endpoint, ')
          ..write('localFilePath: $localFilePath, ')
          ..write('label: $label, ')
          ..write('createdAt: $createdAt, ')
          ..write('attemptCount: $attemptCount, ')
          ..write('lastError: $lastError, ')
          ..write('deadLetter: $deadLetter')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $PendingSyncOperationsTable pendingSyncOperations =
      $PendingSyncOperationsTable(this);
  late final $CachedSyncGroupsTable cachedSyncGroups = $CachedSyncGroupsTable(
    this,
  );
  late final $PendingAttachmentsTable pendingAttachments =
      $PendingAttachmentsTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    pendingSyncOperations,
    cachedSyncGroups,
    pendingAttachments,
  ];
}

typedef $$PendingSyncOperationsTableCreateCompanionBuilder =
    PendingSyncOperationsCompanion Function({
      Value<int> id,
      required String entityType,
      required String payloadJson,
      Value<DateTime> createdAt,
      Value<int> attemptCount,
      Value<String?> lastError,
      Value<bool> deadLetter,
    });
typedef $$PendingSyncOperationsTableUpdateCompanionBuilder =
    PendingSyncOperationsCompanion Function({
      Value<int> id,
      Value<String> entityType,
      Value<String> payloadJson,
      Value<DateTime> createdAt,
      Value<int> attemptCount,
      Value<String?> lastError,
      Value<bool> deadLetter,
    });

class $$PendingSyncOperationsTableFilterComposer
    extends Composer<_$AppDatabase, $PendingSyncOperationsTable> {
  $$PendingSyncOperationsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get entityType => $composableBuilder(
    column: $table.entityType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get attemptCount => $composableBuilder(
    column: $table.attemptCount,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get lastError => $composableBuilder(
    column: $table.lastError,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get deadLetter => $composableBuilder(
    column: $table.deadLetter,
    builder: (column) => ColumnFilters(column),
  );
}

class $$PendingSyncOperationsTableOrderingComposer
    extends Composer<_$AppDatabase, $PendingSyncOperationsTable> {
  $$PendingSyncOperationsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get entityType => $composableBuilder(
    column: $table.entityType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get attemptCount => $composableBuilder(
    column: $table.attemptCount,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get lastError => $composableBuilder(
    column: $table.lastError,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get deadLetter => $composableBuilder(
    column: $table.deadLetter,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$PendingSyncOperationsTableAnnotationComposer
    extends Composer<_$AppDatabase, $PendingSyncOperationsTable> {
  $$PendingSyncOperationsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get entityType => $composableBuilder(
    column: $table.entityType,
    builder: (column) => column,
  );

  GeneratedColumn<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<int> get attemptCount => $composableBuilder(
    column: $table.attemptCount,
    builder: (column) => column,
  );

  GeneratedColumn<String> get lastError =>
      $composableBuilder(column: $table.lastError, builder: (column) => column);

  GeneratedColumn<bool> get deadLetter => $composableBuilder(
    column: $table.deadLetter,
    builder: (column) => column,
  );
}

class $$PendingSyncOperationsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $PendingSyncOperationsTable,
          PendingSyncRow,
          $$PendingSyncOperationsTableFilterComposer,
          $$PendingSyncOperationsTableOrderingComposer,
          $$PendingSyncOperationsTableAnnotationComposer,
          $$PendingSyncOperationsTableCreateCompanionBuilder,
          $$PendingSyncOperationsTableUpdateCompanionBuilder,
          (
            PendingSyncRow,
            BaseReferences<
              _$AppDatabase,
              $PendingSyncOperationsTable,
              PendingSyncRow
            >,
          ),
          PendingSyncRow,
          PrefetchHooks Function()
        > {
  $$PendingSyncOperationsTableTableManager(
    _$AppDatabase db,
    $PendingSyncOperationsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PendingSyncOperationsTableFilterComposer(
                $db: db,
                $table: table,
              ),
          createOrderingComposer: () =>
              $$PendingSyncOperationsTableOrderingComposer(
                $db: db,
                $table: table,
              ),
          createComputedFieldComposer: () =>
              $$PendingSyncOperationsTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> entityType = const Value.absent(),
                Value<String> payloadJson = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> attemptCount = const Value.absent(),
                Value<String?> lastError = const Value.absent(),
                Value<bool> deadLetter = const Value.absent(),
              }) => PendingSyncOperationsCompanion(
                id: id,
                entityType: entityType,
                payloadJson: payloadJson,
                createdAt: createdAt,
                attemptCount: attemptCount,
                lastError: lastError,
                deadLetter: deadLetter,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String entityType,
                required String payloadJson,
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> attemptCount = const Value.absent(),
                Value<String?> lastError = const Value.absent(),
                Value<bool> deadLetter = const Value.absent(),
              }) => PendingSyncOperationsCompanion.insert(
                id: id,
                entityType: entityType,
                payloadJson: payloadJson,
                createdAt: createdAt,
                attemptCount: attemptCount,
                lastError: lastError,
                deadLetter: deadLetter,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$PendingSyncOperationsTable, PendingSyncRow>(
                    table,
                  ),
                  BaseReferences<
                    _$AppDatabase,
                    $PendingSyncOperationsTable,
                    PendingSyncRow
                  >(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$PendingSyncOperationsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $PendingSyncOperationsTable,
      PendingSyncRow,
      $$PendingSyncOperationsTableFilterComposer,
      $$PendingSyncOperationsTableOrderingComposer,
      $$PendingSyncOperationsTableAnnotationComposer,
      $$PendingSyncOperationsTableCreateCompanionBuilder,
      $$PendingSyncOperationsTableUpdateCompanionBuilder,
      (
        PendingSyncRow,
        BaseReferences<
          _$AppDatabase,
          $PendingSyncOperationsTable,
          PendingSyncRow
        >,
      ),
      PendingSyncRow,
      PrefetchHooks Function()
    >;
typedef $$CachedSyncGroupsTableCreateCompanionBuilder =
    CachedSyncGroupsCompanion Function({
      required String syncGroup,
      required String dataJson,
      required DateTime lastSyncedAt,
      Value<int> rowid,
    });
typedef $$CachedSyncGroupsTableUpdateCompanionBuilder =
    CachedSyncGroupsCompanion Function({
      Value<String> syncGroup,
      Value<String> dataJson,
      Value<DateTime> lastSyncedAt,
      Value<int> rowid,
    });

class $$CachedSyncGroupsTableFilterComposer
    extends Composer<_$AppDatabase, $CachedSyncGroupsTable> {
  $$CachedSyncGroupsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get syncGroup => $composableBuilder(
    column: $table.syncGroup,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get dataJson => $composableBuilder(
    column: $table.dataJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get lastSyncedAt => $composableBuilder(
    column: $table.lastSyncedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedSyncGroupsTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedSyncGroupsTable> {
  $$CachedSyncGroupsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get syncGroup => $composableBuilder(
    column: $table.syncGroup,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get dataJson => $composableBuilder(
    column: $table.dataJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get lastSyncedAt => $composableBuilder(
    column: $table.lastSyncedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedSyncGroupsTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedSyncGroupsTable> {
  $$CachedSyncGroupsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get syncGroup =>
      $composableBuilder(column: $table.syncGroup, builder: (column) => column);

  GeneratedColumn<String> get dataJson =>
      $composableBuilder(column: $table.dataJson, builder: (column) => column);

  GeneratedColumn<DateTime> get lastSyncedAt => $composableBuilder(
    column: $table.lastSyncedAt,
    builder: (column) => column,
  );
}

class $$CachedSyncGroupsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedSyncGroupsTable,
          CachedSyncGroupRow,
          $$CachedSyncGroupsTableFilterComposer,
          $$CachedSyncGroupsTableOrderingComposer,
          $$CachedSyncGroupsTableAnnotationComposer,
          $$CachedSyncGroupsTableCreateCompanionBuilder,
          $$CachedSyncGroupsTableUpdateCompanionBuilder,
          (
            CachedSyncGroupRow,
            BaseReferences<
              _$AppDatabase,
              $CachedSyncGroupsTable,
              CachedSyncGroupRow
            >,
          ),
          CachedSyncGroupRow,
          PrefetchHooks Function()
        > {
  $$CachedSyncGroupsTableTableManager(
    _$AppDatabase db,
    $CachedSyncGroupsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedSyncGroupsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedSyncGroupsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedSyncGroupsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> syncGroup = const Value.absent(),
                Value<String> dataJson = const Value.absent(),
                Value<DateTime> lastSyncedAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedSyncGroupsCompanion(
                syncGroup: syncGroup,
                dataJson: dataJson,
                lastSyncedAt: lastSyncedAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String syncGroup,
                required String dataJson,
                required DateTime lastSyncedAt,
                Value<int> rowid = const Value.absent(),
              }) => CachedSyncGroupsCompanion.insert(
                syncGroup: syncGroup,
                dataJson: dataJson,
                lastSyncedAt: lastSyncedAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$CachedSyncGroupsTable, CachedSyncGroupRow>(
                    table,
                  ),
                  BaseReferences<
                    _$AppDatabase,
                    $CachedSyncGroupsTable,
                    CachedSyncGroupRow
                  >(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedSyncGroupsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedSyncGroupsTable,
      CachedSyncGroupRow,
      $$CachedSyncGroupsTableFilterComposer,
      $$CachedSyncGroupsTableOrderingComposer,
      $$CachedSyncGroupsTableAnnotationComposer,
      $$CachedSyncGroupsTableCreateCompanionBuilder,
      $$CachedSyncGroupsTableUpdateCompanionBuilder,
      (
        CachedSyncGroupRow,
        BaseReferences<
          _$AppDatabase,
          $CachedSyncGroupsTable,
          CachedSyncGroupRow
        >,
      ),
      CachedSyncGroupRow,
      PrefetchHooks Function()
    >;
typedef $$PendingAttachmentsTableCreateCompanionBuilder =
    PendingAttachmentsCompanion Function({
      Value<int> id,
      required String endpoint,
      required String localFilePath,
      required String label,
      Value<DateTime> createdAt,
      Value<int> attemptCount,
      Value<String?> lastError,
      Value<bool> deadLetter,
    });
typedef $$PendingAttachmentsTableUpdateCompanionBuilder =
    PendingAttachmentsCompanion Function({
      Value<int> id,
      Value<String> endpoint,
      Value<String> localFilePath,
      Value<String> label,
      Value<DateTime> createdAt,
      Value<int> attemptCount,
      Value<String?> lastError,
      Value<bool> deadLetter,
    });

class $$PendingAttachmentsTableFilterComposer
    extends Composer<_$AppDatabase, $PendingAttachmentsTable> {
  $$PendingAttachmentsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get endpoint => $composableBuilder(
    column: $table.endpoint,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get localFilePath => $composableBuilder(
    column: $table.localFilePath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get label => $composableBuilder(
    column: $table.label,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get attemptCount => $composableBuilder(
    column: $table.attemptCount,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get lastError => $composableBuilder(
    column: $table.lastError,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get deadLetter => $composableBuilder(
    column: $table.deadLetter,
    builder: (column) => ColumnFilters(column),
  );
}

class $$PendingAttachmentsTableOrderingComposer
    extends Composer<_$AppDatabase, $PendingAttachmentsTable> {
  $$PendingAttachmentsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get endpoint => $composableBuilder(
    column: $table.endpoint,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get localFilePath => $composableBuilder(
    column: $table.localFilePath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get label => $composableBuilder(
    column: $table.label,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get attemptCount => $composableBuilder(
    column: $table.attemptCount,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get lastError => $composableBuilder(
    column: $table.lastError,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get deadLetter => $composableBuilder(
    column: $table.deadLetter,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$PendingAttachmentsTableAnnotationComposer
    extends Composer<_$AppDatabase, $PendingAttachmentsTable> {
  $$PendingAttachmentsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get endpoint =>
      $composableBuilder(column: $table.endpoint, builder: (column) => column);

  GeneratedColumn<String> get localFilePath => $composableBuilder(
    column: $table.localFilePath,
    builder: (column) => column,
  );

  GeneratedColumn<String> get label =>
      $composableBuilder(column: $table.label, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<int> get attemptCount => $composableBuilder(
    column: $table.attemptCount,
    builder: (column) => column,
  );

  GeneratedColumn<String> get lastError =>
      $composableBuilder(column: $table.lastError, builder: (column) => column);

  GeneratedColumn<bool> get deadLetter => $composableBuilder(
    column: $table.deadLetter,
    builder: (column) => column,
  );
}

class $$PendingAttachmentsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $PendingAttachmentsTable,
          PendingAttachmentRow,
          $$PendingAttachmentsTableFilterComposer,
          $$PendingAttachmentsTableOrderingComposer,
          $$PendingAttachmentsTableAnnotationComposer,
          $$PendingAttachmentsTableCreateCompanionBuilder,
          $$PendingAttachmentsTableUpdateCompanionBuilder,
          (
            PendingAttachmentRow,
            BaseReferences<
              _$AppDatabase,
              $PendingAttachmentsTable,
              PendingAttachmentRow
            >,
          ),
          PendingAttachmentRow,
          PrefetchHooks Function()
        > {
  $$PendingAttachmentsTableTableManager(
    _$AppDatabase db,
    $PendingAttachmentsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PendingAttachmentsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PendingAttachmentsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PendingAttachmentsTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> endpoint = const Value.absent(),
                Value<String> localFilePath = const Value.absent(),
                Value<String> label = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> attemptCount = const Value.absent(),
                Value<String?> lastError = const Value.absent(),
                Value<bool> deadLetter = const Value.absent(),
              }) => PendingAttachmentsCompanion(
                id: id,
                endpoint: endpoint,
                localFilePath: localFilePath,
                label: label,
                createdAt: createdAt,
                attemptCount: attemptCount,
                lastError: lastError,
                deadLetter: deadLetter,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String endpoint,
                required String localFilePath,
                required String label,
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> attemptCount = const Value.absent(),
                Value<String?> lastError = const Value.absent(),
                Value<bool> deadLetter = const Value.absent(),
              }) => PendingAttachmentsCompanion.insert(
                id: id,
                endpoint: endpoint,
                localFilePath: localFilePath,
                label: label,
                createdAt: createdAt,
                attemptCount: attemptCount,
                lastError: lastError,
                deadLetter: deadLetter,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$PendingAttachmentsTable, PendingAttachmentRow>(
                    table,
                  ),
                  BaseReferences<
                    _$AppDatabase,
                    $PendingAttachmentsTable,
                    PendingAttachmentRow
                  >(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$PendingAttachmentsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $PendingAttachmentsTable,
      PendingAttachmentRow,
      $$PendingAttachmentsTableFilterComposer,
      $$PendingAttachmentsTableOrderingComposer,
      $$PendingAttachmentsTableAnnotationComposer,
      $$PendingAttachmentsTableCreateCompanionBuilder,
      $$PendingAttachmentsTableUpdateCompanionBuilder,
      (
        PendingAttachmentRow,
        BaseReferences<
          _$AppDatabase,
          $PendingAttachmentsTable,
          PendingAttachmentRow
        >,
      ),
      PendingAttachmentRow,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$PendingSyncOperationsTableTableManager get pendingSyncOperations =>
      $$PendingSyncOperationsTableTableManager(_db, _db.pendingSyncOperations);
  $$CachedSyncGroupsTableTableManager get cachedSyncGroups =>
      $$CachedSyncGroupsTableTableManager(_db, _db.cachedSyncGroups);
  $$PendingAttachmentsTableTableManager get pendingAttachments =>
      $$PendingAttachmentsTableTableManager(_db, _db.pendingAttachments);
}
