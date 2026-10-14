using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;

namespace CharacterDesigner.Unity.Editor
{
    // Transport JSON must preserve optional nulls. Unity inline serialization cannot do so.
    // Only public DTO fields and the three optional Link-revision DTO properties are emitted;
    // computed asset accessors, serialized backing strings and Unity managed-reference data are excluded.
    public static class CharacterAnimationCompositionJson
    {
        sealed class FieldsResolver : DefaultContractResolver
        {
            protected override List<MemberInfo> GetSerializableMembers(Type type)
            {
                var fields = type.GetFields(BindingFlags.Instance | BindingFlags.Public)
                    .Where(field => !field.IsDefined(typeof(NonSerializedAttribute), false)).Cast<MemberInfo>();
                var optional = type.GetProperties(BindingFlags.Instance | BindingFlags.Public)
                    .Where(property => property.CanRead && property.CanWrite && property.GetIndexParameters().Length == 0 &&
                        (property.Name == "composition" || property.Name == "composition_export" || property.Name == "CompanionHoldComposition") &&
                        (property.PropertyType == typeof(CharacterAnimationComposition) || property.PropertyType == typeof(CharacterAnimationCompositionExport)))
                    .Cast<MemberInfo>();
                return fields.Concat(optional).ToList();
            }
        }

        static readonly JsonSerializerSettings Settings = new()
        {
            ContractResolver = new FieldsResolver(), Culture = CultureInfo.InvariantCulture,
            NullValueHandling = NullValueHandling.Include, TypeNameHandling = TypeNameHandling.None,
            DateParseHandling = DateParseHandling.None, MaxDepth = 64
        };

        public static string ToJson(object value, bool prettyPrint = false) => JsonConvert.SerializeObject(value,
            prettyPrint ? Formatting.Indented : Formatting.None, Settings);
        public static T FromJson<T>(string json) => JsonConvert.DeserializeObject<T>(json, Settings);
    }
}
